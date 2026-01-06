    # apps/logistics/logistics/transport/doctype/transport_order/transport_order.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate
from pymysql.err import ProgrammingError

# keep these exactly as requested
ORDER_LEGS_FIELDNAME_FALLBACKS = ["legs"]
JOB_LEGS_FIELDNAME_FALLBACKS = ["legs"]

# Fields we want to copy over from Sales Quote Transport rows into Transport Order Charges
SALES_QUOTE_CHARGE_FIELDS = [
    "item_code",
    "item_name",
    "calculation_method",
    "quantity",
    "uom",
    "currency",
    "unit_rate",
    "unit_type",
    "minimum_quantity",
    "minimum_charge",
    "maximum_charge",
    "base_amount",
    "estimated_revenue",
    "use_tariff_in_revenue",
    "use_tariff_in_cost",
    "tariff",
    "cost_calculation_method",
    "cost_quantity",
    "cost_uom",
    "cost_currency",
    "unit_cost",
    "cost_unit_type",
    "cost_minimum_quantity",
    "cost_minimum_charge",
    "cost_maximum_charge",
    "cost_base_amount",
    "estimated_cost",
    "revenue_calc_notes",
    "cost_calc_notes",
]


class TransportOrder(Document):
    def validate(self):
        """If the Transport Template changes, clear the Leg Plan table."""
        try:
            if self.has_value_changed("transport_template"):
                legs_field = _find_child_table_fieldname(
                    "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                )
                self.set(legs_field, [])
        except Exception:
            old = getattr(self, "_doc_before_save", None) or self.get_doc_before_save()
            if old and getattr(old, "transport_template", None) != getattr(self, "transport_template", None):
                legs_field = _find_child_table_fieldname(
                    "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                )
                self.set(legs_field, [])
        
        # Validate that pick and drop facilities are different in each leg
        self._validate_leg_facilities()
        
        # Validate transport job type specific rules
        self._validate_transport_job_type()
        
        # Validate vehicle_type is required only if consolidate is not checked
        self._validate_vehicle_type_required()
        
        # Validate load type is allowed for job type
        self.validate_load_type_allowed_for_job()

    def before_submit(self):
        """Validate transport legs before submitting the Transport Order."""
        self._validate_transport_legs()

    def _validate_transport_legs(self):
        """Validate that transport legs have complete details and scheduled_date if filled."""
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        
        if not legs:
            frappe.throw(_("Transport Order must have at least one leg. Please add transport legs before submitting."))
        
        for i, leg in enumerate(legs, 1):
            # Check for required fields
            missing_fields = []
            
            # Check facility details
            if not leg.get("facility_type_from"):
                missing_fields.append("Facility Type From")
            if not leg.get("facility_from"):
                missing_fields.append("Facility From")
            if not leg.get("facility_type_to"):
                missing_fields.append("Facility Type To")
            if not leg.get("facility_to"):
                missing_fields.append("Facility To")
            
            # Check transport details
            if not leg.get("vehicle_type"):
                missing_fields.append("Vehicle Type")
            if not leg.get("transport_job_type"):
                missing_fields.append("Transport Job Type")
            
            # Check pick and drop modes
            if not leg.get("pick_mode"):
                missing_fields.append("Pick Mode")
            if not leg.get("drop_mode"):
                missing_fields.append("Drop Mode")
            
            # Check scheduled_date if it's filled
            if leg.get("scheduled_date"):
                try:
                    from frappe.utils import getdate
                    getdate(leg.scheduled_date)  # Validate date format
                except Exception:
                    frappe.throw(_("Row {0}: Invalid scheduled date format. Please use a valid date format.").format(i))
            
            # Note: day_offset is not a field in Transport Order Legs table
            # It's only used during template mapping
            
            # Report missing fields
            if missing_fields:
                frappe.throw(_("Row {0}: Missing required fields: {1}").format(i, ", ".join(missing_fields)))
            
            # Validate address details if addresses are set (they should be valid Address links)
            # Note: pick_mode and drop_mode are Link fields to Pick and Drop Mode records, not literal strings
            if leg.get("pick_address") and not frappe.db.exists("Address", leg.get("pick_address")):
                frappe.throw(_("Row {0}: Pick address '{1}' does not exist.").format(i, leg.get("pick_address")))
            
            if leg.get("drop_address") and not frappe.db.exists("Address", leg.get("drop_address")):
                frappe.throw(_("Row {0}: Drop address '{1}' does not exist.").format(i, leg.get("drop_address")))
            
            # Auto-fill addresses from facilities if not set
            self._auto_fill_leg_addresses(leg, i)

    def _auto_fill_leg_addresses(self, leg, leg_index):
        """Auto-fill addresses from facilities if not already set.
        
        Preserves existing pick_mode and drop_mode values - only sets pick_address and drop_address.
        pick_mode and drop_mode are Link fields to Pick and Drop Mode records and should not be
        set to literal strings like "Address".
        """
        try:
            # Auto-fill pick address from facility
            # Only set address if not already set, and preserve existing pick_mode value
            if not leg.get("pick_address") and leg.get("facility_type_from") and leg.get("facility_from"):
                facility_doc = frappe.get_doc(leg.facility_type_from, leg.facility_from)
                if hasattr(facility_doc, 'address') and facility_doc.address:
                    leg.pick_address = facility_doc.address
                    # Update the leg in the document - only set pick_address, preserve pick_mode
                    legs_field = _find_child_table_fieldname(
                        "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                    )
                    self.set_value(legs_field, leg_index - 1, "pick_address", facility_doc.address)
                    # Do not modify pick_mode - preserve existing value or leave it unset
            
            # Auto-fill drop address from facility
            # Only set address if not already set, and preserve existing drop_mode value
            if not leg.get("drop_address") and leg.get("facility_type_to") and leg.get("facility_to"):
                facility_doc = frappe.get_doc(leg.facility_type_to, leg.facility_to)
                if hasattr(facility_doc, 'address') and facility_doc.address:
                    leg.drop_address = facility_doc.address
                    # Update the leg in the document - only set drop_address, preserve drop_mode
                    legs_field = _find_child_table_fieldname(
                        "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
                    )
                    self.set_value(legs_field, leg_index - 1, "drop_address", facility_doc.address)
                    # Do not modify drop_mode - preserve existing value or leave it unset
                    
        except Exception as e:
            # Log error but don't fail validation
            frappe.log_error(f"Error auto-filling addresses for leg {leg_index}: {str(e)}", "Transport Order Address Auto-fill")

    def _validate_leg_facilities(self):
        """Validate that pick and drop facilities are different in each leg."""
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        
        for i, leg in enumerate(legs, 1):
            facility_from = leg.get("facility_from")
            facility_to = leg.get("facility_to")
            if facility_from and facility_to and facility_from == facility_to:
                frappe.throw(_("Row {0}: Pick facility and drop facility cannot be the same.").format(i))

    def _validate_transport_job_type(self):
        """Validate transport job type specific business rules."""
        if not self.transport_job_type:
            return
        
        # Container type validations
        if self.transport_job_type == "Container":
            self._validate_container_requirements()
        elif self.transport_job_type == "Heavy Haul":
            self._validate_heavy_haul_requirements()
        elif self.transport_job_type == "Oversized":
            self._validate_oversized_requirements()
        elif self.transport_job_type == "Special":
            self._validate_special_requirements()
        elif self.transport_job_type == "Multimodal":
            self._validate_multimodal_requirements()
        
        # Vehicle type compatibility validation
        self._validate_vehicle_type_compatibility()
        
        # Load type compatibility validation
        self.validate_load_type_allowed_for_job()

    def _validate_container_requirements(self):
        """Validate container-specific requirements."""
        if not self.container_type:
            frappe.throw(_("Container Type is required for Container transport jobs."))
        
        if not self.container_no:
            frappe.throw(_("Container Number is required for Container transport jobs."))
        
        # Validate container number format if needed
        if self.container_no and len(self.container_no) < 4:
            frappe.throw(_("Container Number must be at least 4 characters long."))

    def _validate_heavy_haul_requirements(self):
        """Validate heavy haul specific requirements."""
        # Check if vehicle type is suitable for heavy haul
        if self.vehicle_type:
            vehicle_type_doc = frappe.get_doc("Vehicle Type", self.vehicle_type)
            if hasattr(vehicle_type_doc, 'max_weight') and vehicle_type_doc.max_weight:
                if self.get_total_weight() > vehicle_type_doc.max_weight:
                    frappe.throw(_("Total weight exceeds maximum capacity for selected vehicle type."))
        
        # Check for special permits or documentation
        if not self.internal_notes:
            frappe.msgprint(_("Heavy Haul transport may require special permits. Please add relevant information in Internal Notes."))

    def _validate_oversized_requirements(self):
        """Validate oversized cargo requirements."""
        # Check dimensions if available
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'length') and hasattr(package, 'width') and hasattr(package, 'height'):
                    if (package.length > 12 or package.width > 2.5 or package.height > 4):
                        frappe.msgprint(_("Oversized cargo detected. Special routing and permits may be required."))
                        break
        
        # Check for special handling notes
        if not self.internal_notes:
            frappe.msgprint(_("Oversized transport may require special handling. Please add relevant information in Internal Notes."))

    def _validate_special_requirements(self):
        """Validate special transport requirements."""
        if not self.internal_notes:
            frappe.throw(_("Special transport requires detailed instructions in Internal Notes."))
        
        # Check for hazardous materials
        if self.hazardous:
            frappe.msgprint(_("Hazardous materials require special handling and documentation."))

    def _validate_multimodal_requirements(self):
        """Validate multimodal transport requirements."""
        # Check if multiple transport modes are specified
        if not self.internal_notes:
            frappe.msgprint(_("Multimodal transport requires coordination details in Internal Notes."))
        
        # Validate that legs have different transport modes if applicable
        legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        legs = self.get(legs_field) or []
        if len(legs) < 2:
            frappe.msgprint(_("Multimodal transport typically requires multiple legs."))

    def _validate_vehicle_type_compatibility(self):
        """Validate vehicle type compatibility with transport job type."""
        if not self.vehicle_type or not self.transport_job_type:
            return
        
        # Get vehicle type restrictions
        vehicle_type_doc = frappe.get_doc("Vehicle Type", self.vehicle_type)
        
        # Check if vehicle type is suitable for the job type
        if hasattr(vehicle_type_doc, 'suitable_for'):
            suitable_for = vehicle_type_doc.suitable_for or []
            if self.transport_job_type not in suitable_for:
                frappe.msgprint(_("Selected vehicle type may not be suitable for {0} transport.").format(self.transport_job_type))

    def validate_load_type_allowed_for_job(self):
        """Validate that the selected Load Type is allowed for the chosen Transport Job Type."""
        if not self.load_type or not self.transport_job_type:
            return

        field_map = {
            "Container": "container",
            "Non-Container": "non_container",
            "Special": "special",
            "Oversized": "oversized",
            "Multimodal": "multimodal",
            "Heavy Haul": "heavy_haul"
        }

        allowed_field = field_map.get(self.transport_job_type)
        if not allowed_field:
            return

        allowed = frappe.db.get_value(
            "Load Type",
            self.load_type,
            allowed_field
        )

        if not allowed:
            frappe.throw(
                _(f"Load Type {self.load_type} is not allowed for {self.transport_job_type} jobs.")
            )

    def _validate_vehicle_type_required(self):
        """Validate that vehicle_type is required only if consolidate is not checked."""
        # Vehicle Type is mandatory only if Consolidate checkbox is not checked
        if not self.vehicle_type and not self.consolidate:
            frappe.throw(_("Vehicle Type is required when Consolidate is not checked"))

    def get_total_weight(self):
        """Calculate total weight from packages."""
        total_weight = 0
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'weight') and package.weight:
                    total_weight += float(package.weight or 0)
        return total_weight

    def get_total_volume(self):
        """Calculate total volume from packages."""
        total_volume = 0
        if hasattr(self, 'packages') and self.packages:
            for package in self.packages:
                if hasattr(package, 'volume') and package.volume:
                    total_volume += float(package.volume or 0)
        return total_volume

    def get_required_permits(self):
        """Get list of required permits based on transport job type."""
        permits = []
        
        if self.transport_job_type == "Heavy Haul":
            permits.extend(["Heavy Vehicle Permit", "Oversize Load Permit"])
        elif self.transport_job_type == "Oversized":
            permits.extend(["Oversize Load Permit", "Route Clearance"])
        elif self.transport_job_type == "Special":
            permits.extend(["Special Transport Permit"])
        elif self.transport_job_type == "Hazardous":
            permits.extend(["Hazardous Materials Permit", "Environmental Clearance"])
        
        if self.hazardous:
            permits.extend(["Hazardous Materials Permit", "Environmental Clearance"])
        
        return list(set(permits))  # Remove duplicates

    def get_estimated_cost_factors(self):
        """Get cost factors based on transport job type."""
        factors = {
            "base_rate": 1.0,
            "surcharge": 0.0,
            "special_handling": False
        }
        
        if self.transport_job_type == "Heavy Haul":
            factors["surcharge"] = 0.5  # 50% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Oversized":
            factors["surcharge"] = 0.3  # 30% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Special":
            factors["surcharge"] = 0.4  # 40% surcharge
            factors["special_handling"] = True
        elif self.transport_job_type == "Multimodal":
            factors["surcharge"] = 0.2  # 20% surcharge
        
        if self.hazardous:
            factors["surcharge"] += 0.3  # Additional 30% for hazardous
            factors["special_handling"] = True
        
        if self.refrigeration:
            factors["surcharge"] += 0.2  # Additional 20% for refrigeration
        
        return factors

    def get_vehicle_requirements(self):
        """Get vehicle requirements based on transport job type."""
        requirements = {
            "min_capacity_weight": 0,
            "min_capacity_volume": 0,
            "special_equipment": [],
            "driver_qualifications": []
        }
        
        if self.transport_job_type == "Heavy Haul":
            requirements["min_capacity_weight"] = 50000  # 50 tons
            requirements["special_equipment"].extend(["Heavy Duty Trailer", "Crane"])
            requirements["driver_qualifications"].extend(["Heavy Vehicle License", "Crane Operator License"])
        elif self.transport_job_type == "Oversized":
            requirements["min_capacity_volume"] = 100  # 100 m³
            requirements["special_equipment"].extend(["Oversize Trailer", "Escort Vehicle"])
            requirements["driver_qualifications"].extend(["Oversize Load License"])
        elif self.transport_job_type == "Special":
            requirements["special_equipment"].extend(["Specialized Equipment"])
            requirements["driver_qualifications"].extend(["Special Transport License"])
        
        if self.hazardous:
            requirements["special_equipment"].extend(["Hazmat Equipment"])
            requirements["driver_qualifications"].extend(["Hazmat License"])
        
        if self.refrigeration:
            requirements["special_equipment"].extend(["Refrigerated Unit"])
            requirements["driver_qualifications"].extend(["Temperature Control Training"])
        
        return requirements

    def get_consolidation_eligibility(self):
        """Check if this transport order can be consolidated with others."""
        if not self.transport_job_type or not self.load_type:
            return False
        
        # Get load type document
        try:
            load_type_doc = frappe.get_doc("Load Type", self.load_type)
            if not getattr(load_type_doc, 'can_consolidate', False):
                return False
            
            # Check if job type is suitable for consolidation
            if self.transport_job_type in ["Heavy Haul", "Oversized", "Special"]:
                return False  # These typically cannot be consolidated
            
            return True
        except Exception:
            return False

    def get_estimated_duration(self):
        """Get estimated duration based on transport job type."""
        base_duration = 2  # hours
        
        if self.transport_job_type == "Heavy Haul":
            return base_duration * 3  # 6 hours
        elif self.transport_job_type == "Oversized":
            return base_duration * 2.5  # 5 hours
        elif self.transport_job_type == "Special":
            return base_duration * 2  # 4 hours
        elif self.transport_job_type == "Multimodal":
            return base_duration * 4  # 8 hours
        else:
            return base_duration  # 2 hours

    def get_priority_score(self):
        """Calculate priority score based on transport job type and other factors."""
        score = 0
        
        # Base score by job type
        if self.transport_job_type == "Heavy Haul":
            score += 10
        elif self.transport_job_type == "Oversized":
            score += 8
        elif self.transport_job_type == "Special":
            score += 6
        elif self.transport_job_type == "Multimodal":
            score += 4
        else:
            score += 2
        
        # Additional factors
        if self.hazardous:
            score += 5
        if self.refrigeration:
            score += 3
        
        return score

    def get_route_restrictions(self):
        """Get route restrictions based on transport job type."""
        restrictions = []
        
        if self.transport_job_type == "Heavy Haul":
            restrictions.extend(["No Low Bridges", "Heavy Vehicle Routes Only"])
        elif self.transport_job_type == "Oversized":
            restrictions.extend(["Oversize Load Routes", "Escort Required"])
        elif self.transport_job_type == "Hazardous":
            restrictions.extend(["Hazmat Routes", "No Residential Areas"])
        
        return restrictions

    def on_change(self):
        """Handle changes to the document."""
        if self.has_value_changed("sales_quote"):
            if self.sales_quote:
                self._populate_charges_from_sales_quote()
            else:
                # Clear charges if sales_quote is removed
                self.set("charges", [])
                frappe.msgprint(
                    "Charges cleared as Sales Quote was removed",
                    title="Charges Updated",
                    indicator="blue"
                )

    def _populate_charges_from_sales_quote(self):
        """Populate charges based on sales_quote_transport of the filled sales_quote."""
        if not self.sales_quote:
            return

        try:
            # Verify that the sales_quote exists
            if not frappe.db.exists("Sales Quote", self.sales_quote):
                frappe.msgprint(
                    f"Sales Quote {self.sales_quote} does not exist",
                    title="Error",
                    indicator="red"
                )
                return

            # Clear existing charges
            self.set("charges", [])

            # Fetch sales_quote_transport records from the selected sales_quote
            fields_to_fetch = ["name"] + SALES_QUOTE_CHARGE_FIELDS
            sales_quote_transport_records = frappe.get_all(
                "Sales Quote Transport",
                filters={"parent": self.sales_quote, "parenttype": "Sales Quote"},
                fields=fields_to_fetch,
                order_by="idx"
            )

            if not sales_quote_transport_records:
                frappe.msgprint(
                    f"No transport charges found in Sales Quote: {self.sales_quote}",
                    title="No Charges Found",
                    indicator="orange"
                )
                return

            # Map and populate charges
            charges_added = 0
            for sqt_record in sales_quote_transport_records:
                charge_row = self._map_sales_quote_transport_to_charge(sqt_record)
                if charge_row:
                    self.append("charges", charge_row)
                    charges_added += 1

            if charges_added > 0:
                frappe.msgprint(
                    f"Successfully populated {charges_added} charges from Sales Quote: {self.sales_quote}",
                    title="Charges Updated",
                    indicator="green"
                )
            else:
                frappe.msgprint(
                    f"No valid charges could be mapped from Sales Quote: {self.sales_quote}",
                    title="No Valid Charges",
                    indicator="orange"
                )

        except Exception as e:
            frappe.log_error(
                f"Error populating charges from sales quote {self.sales_quote}: {str(e)}",
                "Transport Order Charges Population Error"
            )
            frappe.msgprint(
                f"Error populating charges: {str(e)}",
                title="Error",
                indicator="red"
            )

    def _map_sales_quote_transport_to_charge(self, sqt_record):
        """Map sales_quote_transport record to transport_order_charges format."""
        try:
            # Map overlapping fields directly
            charge_data = {}
            for field in SALES_QUOTE_CHARGE_FIELDS:
                if field in sqt_record:
                    charge_data[field] = sqt_record.get(field)

            # Fallbacks for essential fields
            if not charge_data.get("item_name") and sqt_record.get("item_code"):
                item_doc = frappe.get_doc("Item", sqt_record.item_code)
                charge_data["item_name"] = item_doc.item_name

            if not charge_data.get("uom") and sqt_record.get("item_code"):
                item_doc = item_doc if "item_doc" in locals() else frappe.get_doc("Item", sqt_record.item_code)
                charge_data["uom"] = item_doc.stock_uom

            if charge_data.get("unit_rate") is None:
                charge_data["unit_rate"] = 0

            if not charge_data.get("quantity"):
                charge_data["quantity"] = 1

            return charge_data

        except Exception as e:
            frappe.log_error(
                f"Error mapping sales quote transport record: {str(e)}",
                "Transport Order Charge Mapping Error"
            )
            return None


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------
def _find_child_table_fieldname(parent_dt: str, child_dt: str, fallbacks: Optional[List[str]] = None) -> str:
    """Find the Table field on parent_dt that points to child_dt, else try fallbacks."""
    meta = frappe.get_meta(parent_dt)
    for df in meta.fields:
        if df.fieldtype == "Table" and (df.options or "").strip() == child_dt:
            return df.fieldname

    for guess in (fallbacks or []):
        if meta.has_field(guess):
            df = meta.get_field(guess)
            if getattr(df, "fieldtype", None) == "Table":
                return guess

    table_fields = [f"{df.fieldname} -> {df.options}" for df in meta.fields if df.fieldtype == "Table"]
    frappe.throw(
        _(
            "Could not find a child Table field on {parent} that points to {child}. "
            "Table fields found: {found}"
        ).format(parent=parent_dt, child=child_dt, found=", ".join(table_fields))
    )


def _get_template_child_dt() -> Tuple[str, str]:
    """Return (child_doctype, fieldname_on_template) for Transport Template."""
    meta = frappe.get_meta("Transport Template")
    for df in meta.fields:
        if df.fieldtype == "Table" and df.options:
            return df.options, df.fieldname
    # sensible default
    return "Transport Template Leg", "legs"


def _has_field(doctype: str, fieldname: str) -> bool:
    try:
        return frappe.get_meta(doctype).has_field(fieldname)
    except Exception:
        return False


def _coalesce(obj: Any, names: List[str], default=None):
    """Return first non-None attribute/key from names on obj."""
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v is not None:
                return v
        if isinstance(obj, dict) and n in obj:
            v = obj.get(n)
            if v is not None:
                return v
    return default


def _fetch_template_legs(template_name: str) -> List[Dict[str, Any]]:
    """
    Pull ordered legs from Transport Template's child table.
    Only includes fields that exist on the child doctype to keep it schema-safe.
    """
    if not template_name:
        frappe.throw("Please select a Transport Template first.")

    child_dt, _child_field = _get_template_child_dt()
    child_meta = frappe.get_meta(child_dt)

    # fields we commonly expect on a template leg
    candidates = [
        "facility_type_from",
        "facility_from",
        "pick_mode",
        "pick_address",
        "facility_type_to",
        "facility_to",
        "drop_mode",
        "drop_address",
        "vehicle_type",
        "transport_job_type",
        # for scheduling:
        "day_offset",
        "offset_days",
        "days_offset",
    ]

    fields = ["name", "idx"]
    for f in candidates:
        if child_meta.has_field(f):
            fields.append(f)

    rows = frappe.get_all(
        child_dt,
        filters={"parent": template_name, "parenttype": "Transport Template"},
        fields=fields,
        order_by="idx asc",
    )
    return rows or []


def _map_template_row_to_order_row(order_child_dt: str, tmpl_row: Dict[str, Any], base_date) -> Dict[str, Any]:
    """
    Map template leg fields onto Transport Order Legs row (only for fields that exist on the child doctype).
    Computes scheduled_date using day_offset when possible.
    """
    out: Dict[str, Any] = {}

    def set_if(field: str, value):
        if _has_field(order_child_dt, field):
            out[field] = value

    # copy common fields
    set_if("facility_type_from", _coalesce(tmpl_row, ["facility_type_from", "from_type"]))
    set_if("facility_from", _coalesce(tmpl_row, ["facility_from", "from_name"]))
    set_if("pick_mode", _coalesce(tmpl_row, ["pick_mode"]))
    set_if("pick_address", _coalesce(tmpl_row, ["pick_address"]))

    set_if("facility_type_to", _coalesce(tmpl_row, ["facility_type_to", "to_type"]))
    set_if("facility_to", _coalesce(tmpl_row, ["facility_to", "to_name"]))
    set_if("drop_mode", _coalesce(tmpl_row, ["drop_mode"]))
    set_if("drop_address", _coalesce(tmpl_row, ["drop_address"]))

    set_if("vehicle_type", _coalesce(tmpl_row, ["vehicle_type", "vt"]))
    set_if("transport_job_type", _coalesce(tmpl_row, ["transport_job_type", "job_type"]))
    set_if("priority", _coalesce(tmpl_row, ["priority"]))

    # day offset → scheduled_date
    raw_off = _coalesce(tmpl_row, ["day_offset", "offset_days", "days_offset"], 0)
    try:
        offset = cint(raw_off or 0)
    except Exception:
        offset = 0
    if base_date and _has_field(order_child_dt, "scheduled_date"):
        try:
            set_if("scheduled_date", add_days(base_date, offset))
        except Exception:
            set_if("scheduled_date", base_date)

    # keep the offset if child table has a field for it
    set_if("day_offset", offset)

    return out


# -------------------------------------------------------------------
# Whitelisted actions
# -------------------------------------------------------------------
@frappe.whitelist()
def action_get_leg_plan(docname: str, replace: int = 1, save: int = 1):
    """Populate Transport Order legs from the selected Transport Template."""
    if not docname:
        frappe.throw("Missing Transport Order name.")

    doc = frappe.get_doc("Transport Order", docname)

    # discover order child table dt/field
    order_child_dt = "Transport Order Legs"
    order_child_field = _find_child_table_fieldname(
        "Transport Order", order_child_dt, ORDER_LEGS_FIELDNAME_FALLBACKS
    )

    template_name = _coalesce(doc, ["transport_template", "template", "template_name"])
    if not template_name:
        frappe.throw("Please choose a Transport Template on this order first.")

    template_rows = _fetch_template_legs(template_name)
    if not template_rows:
        frappe.throw(f"No legs found in template: {frappe.bold(template_name)}")

    base_date = None
    if getattr(doc, "scheduled_date", None):
        try:
            base_date = getdate(doc.scheduled_date)
        except Exception:
            base_date = None

    if cint(replace):
        doc.set(order_child_field, [])

    created = 0
    for tr in template_rows:
        row_data = _map_template_row_to_order_row(order_child_dt, tr, base_date)
        if not row_data:
            continue
        
        # Auto-fill transport_job_type and vehicle_type from parent if not set in template
        if not row_data.get("transport_job_type") and getattr(doc, "transport_job_type", None):
            row_data["transport_job_type"] = doc.transport_job_type
        
        if not row_data.get("vehicle_type") and getattr(doc, "vehicle_type", None):
            row_data["vehicle_type"] = doc.vehicle_type
        
        doc.append(order_child_field, row_data)
        created += 1

    if cint(save):
        doc.flags.ignore_permissions = True
        doc.save()

    # --- build UI message safely ---
    base_label = frappe.utils.formatdate(base_date) if base_date else "—"
    mode_label = "Replace" if cint(replace) else "Append"

    html = f"""
        <div>
            <div style="font-weight:600;margin-bottom:6px;">
                {_('Template')}: {frappe.utils.escape_html(template_name)}
            </div>
            <ul style="margin:0 0 8px 16px;padding:0;">
                <li>{_('Base date')}: {base_label}</li>
                <li>{_('Legs added')}: <b>{created}</b></li>
                <li>{_('Mode')}: {mode_label}</li>
            </ul>
        </div>
    """
    frappe.msgprint(html, title=_("Leg plan created"), indicator="green")

    return {
        "ok": True,
        "order": docname,
        "template": template_name,
        "base_date": str(base_date) if base_date else None,
        "legs_added": created,
        "replaced": bool(cint(replace)),
        "saved": bool(cint(save)),
    }

# -------------------------------------------------------------------
# ACTION: Create Transport Job from a submitted Transport Order
# -------------------------------------------------------------------
@frappe.whitelist()
def action_create_transport_job(docname: str):
    """Create (or reuse) a Transport Job from a submitted Transport Order."""
    try:
        doc = frappe.get_doc("Transport Order", docname)

        if doc.docstatus != 1:
            frappe.throw(_("Please submit the Transport Order before creating a Transport Job."))

        # Reuse if already created
        existing = frappe.db.get_value("Transport Job", {"transport_order": doc.name}, "name")
        if existing:
            return {"name": existing, "created": False, "already_exists": True}

        job = frappe.new_doc("Transport Job")
        job_meta = frappe.get_meta(job.doctype)

        # ---- Header field mapping (TO -> TJ)
        header_map = {
            "transport_order": doc.name,
            "transport_template": getattr(doc, "transport_template", None),
            "transport_job_type": getattr(doc, "transport_job_type", None),
            "customer": getattr(doc, "customer", None),
            "booking_date": getattr(doc, "booking_date", None),
            "customer_ref_no": getattr(doc, "customer_ref_no", None),
            "hazardous": getattr(doc, "hazardous", None),
            "refrigeration": getattr(doc, "refrigeration", None),
            "vehicle_type": getattr(doc, "vehicle_type", None),
            "load_type": getattr(doc, "load_type", None),
            "container_type": getattr(doc, "container_type", None),
            "container_no": getattr(doc, "container_no", None),
            "consolidate": getattr(doc, "consolidate", None),
            "pick_address": getattr(doc, "pick_address", None),
            "drop_address": getattr(doc, "drop_address", None),
            "company": getattr(doc, "company", None),
            "branch": getattr(doc, "branch", None),
            "cost_center": getattr(doc, "cost_center", None),
            "profit_center": getattr(doc, "profit_center", None),
        }
        for k, v in header_map.items():
            if v is not None and job_meta.has_field(k):
                job.set(k, v)

        # ---- Packages (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field="packages", dst_doc=job, dst_table_field="packages"
        )

        # ---- Charges (TO -> TJ) by common fields
        _copy_child_rows_by_common_fields(
            src_doc=doc, src_table_field="charges", dst_doc=job, dst_table_field="charges"
        )

        # Insert now to get a real job name for back-references from Transport Leg
        # Temporarily ignore mandatory and validation checks to prevent "Job Type must be set first" popups
        # The transport_job_type is set, but conditional field validation may trigger prematurely
        job.flags.ignore_mandatory = True
        job.flags.ignore_validate = True
        job.insert(ignore_permissions=False)

        # ---- Legs: create top-level Transport Leg for each TO leg, then link into TJ legs
        order_legs_field = _find_child_table_fieldname(
            "Transport Order", "Transport Order Legs", ORDER_LEGS_FIELDNAME_FALLBACKS
        )
        job_legs_field = _find_child_table_fieldname(
            "Transport Job", "Transport Job Legs", JOB_LEGS_FIELDNAME_FALLBACKS
        )

        _create_and_attach_job_legs_from_order_legs(
            order_doc=doc,
            job_doc=job,
            order_legs_field=order_legs_field,
            job_legs_field=job_legs_field,
        )

        # Save added legs to job
        job.save(ignore_permissions=False)
        frappe.db.commit()
        return {"name": job.name, "created": True, "already_exists": False}
        
    except Exception as e:
        frappe.log_error(f"Error creating transport job: {str(e)}")
        frappe.throw(_("Failed to create Transport Job: {0}").format(str(e)))


# -------------------------------------------------------------------
# API Endpoints for Transport Job Type functionality
# -------------------------------------------------------------------

@frappe.whitelist()
def get_transport_job_type_info(transport_job_type: str) -> Dict[str, Any]:
    """Get information about a specific transport job type."""
    if not transport_job_type:
        return {}
    
    info = {
        "name": transport_job_type,
        "description": "",
        "requirements": [],
        "restrictions": [],
        "cost_factors": {},
        "vehicle_requirements": {}
    }
    
    if transport_job_type == "Container":
        info.update({
            "description": "Standardized container transport",
            "requirements": ["Container Type", "Container Number"],
            "restrictions": ["Standard Routes", "Container Handling Equipment"]
        })
    elif transport_job_type == "Heavy Haul":
        info.update({
            "description": "Heavy cargo transport requiring specialized equipment",
            "requirements": ["Heavy Vehicle Permit", "Route Clearance", "Special Equipment"],
            "restrictions": ["No Low Bridges", "Heavy Vehicle Routes Only"]
        })
    elif transport_job_type == "Oversized":
        info.update({
            "description": "Oversized cargo transport requiring special routing",
            "requirements": ["Oversize Load Permit", "Escort Vehicle", "Route Planning"],
            "restrictions": ["Oversize Load Routes", "Escort Required"]
        })
    elif transport_job_type == "Special":
        info.update({
            "description": "Special transport requiring custom handling",
            "requirements": ["Special Transport Permit", "Custom Equipment"],
            "restrictions": ["Special Routes", "Custom Handling"]
        })
    elif transport_job_type == "Multimodal":
        info.update({
            "description": "Transport involving multiple modes of transportation",
            "requirements": ["Multi-mode Coordination", "Transfer Planning"],
            "restrictions": ["Mode-specific Routes", "Transfer Points"]
        })
    elif transport_job_type == "Non-Container":
        info.update({
            "description": "General cargo transport without containers",
            "requirements": ["Standard Equipment"],
            "restrictions": ["Standard Routes"]
        })
    
    return info


@frappe.whitelist()
def get_vehicle_compatibility(transport_job_type: str, vehicle_type: str = None) -> Dict[str, Any]:
    """Get vehicle compatibility information for a transport job type."""
    if not transport_job_type:
        return {}
    
    compatibility = {
        "suitable_vehicle_types": [],
        "required_capacity": {},
        "special_equipment": [],
        "driver_qualifications": []
    }
    
    if transport_job_type == "Heavy Haul":
        compatibility.update({
            "suitable_vehicle_types": ["Heavy Truck", "Crane Truck", "Low Loader"],
            "required_capacity": {"min_weight": 50000, "min_volume": 0},
            "special_equipment": ["Heavy Duty Trailer", "Crane", "Winch"],
            "driver_qualifications": ["Heavy Vehicle License", "Crane Operator License"]
        })
    elif transport_job_type == "Oversized":
        compatibility.update({
            "suitable_vehicle_types": ["Oversize Truck", "Flatbed", "Low Loader"],
            "required_capacity": {"min_weight": 0, "min_volume": 100},
            "special_equipment": ["Oversize Trailer", "Escort Vehicle", "Warning Lights"],
            "driver_qualifications": ["Oversize Load License", "Escort Training"]
        })
    elif transport_job_type == "Container":
        compatibility.update({
            "suitable_vehicle_types": ["Container Truck", "Flatbed"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Container Chassis", "Twist Locks"],
            "driver_qualifications": ["Container Handling License"]
        })
    elif transport_job_type == "Special":
        compatibility.update({
            "suitable_vehicle_types": ["Specialized Vehicle", "Custom Truck"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Specialized Equipment", "Custom Trailer"],
            "driver_qualifications": ["Special Transport License", "Custom Training"]
        })
    elif transport_job_type == "Multimodal":
        compatibility.update({
            "suitable_vehicle_types": ["Multi-purpose Vehicle", "Transfer Truck"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Transfer Equipment", "Loading Equipment"],
            "driver_qualifications": ["Multi-mode License", "Transfer Training"]
        })
    else:  # Non-Container
        compatibility.update({
            "suitable_vehicle_types": ["Standard Truck", "Van", "Pickup"],
            "required_capacity": {"min_weight": 0, "min_volume": 0},
            "special_equipment": ["Standard Equipment"],
            "driver_qualifications": ["Standard License"]
        })
    
    return compatibility


@frappe.whitelist()
def get_allowed_vehicle_types(transport_job_type: str, refrigeration: bool = False) -> Dict[str, Any]:
    """Get allowed vehicle types for a transport job type based on boolean columns and reefer."""
    if not transport_job_type:
        return {"vehicle_types": []}
    
    filters = {}
    
    # Filter by container flag
    if transport_job_type == "Container":
        # For Container job type, only allow container vehicle types
        filters["container"] = 1
    elif transport_job_type == "Non-Container":
        # For Non-Container job type, exclude container vehicle types
        filters["container"] = 0
    
    # Filter by boolean columns for specific transport job types
    if transport_job_type == "Special":
        filters["special"] = 1
        # Special job type also requires reefer
        filters["reefer"] = 1
    elif transport_job_type == "Oversized":
        filters["oversized"] = 1
    elif transport_job_type == "Heavy Haul":
        filters["heavy_haul"] = 1
    elif transport_job_type == "Multimodal":
        # Check if multimodal field exists in Vehicle Type doctype
        meta = frappe.get_meta("Vehicle Type")
        if meta.has_field("multimodal"):
            filters["multimodal"] = 1
    
    # Filter by reefer if refrigeration is required (for other job types)
    # Note: Special job type already has reefer=1 filter above
    if refrigeration and transport_job_type != "Special":
        filters["reefer"] = 1
    
    # Get vehicle types matching the filter
    vehicle_types = frappe.get_all(
        "Vehicle Type",
        filters=filters,
        fields=["name", "code", "description", "container", "reefer"],
        order_by="code"
    )
    
    return {"vehicle_types": vehicle_types}


@frappe.whitelist()
def validate_vehicle_job_type_compatibility(transport_job_type: str, vehicle_type: str, refrigeration: bool = False) -> Dict[str, Any]:
    """Validate if a vehicle type is compatible with the transport job type based on boolean columns and refrigeration requirements."""
    if not transport_job_type or not vehicle_type:
        return {"compatible": True, "message": ""}
    
    # Get vehicle type details - fetch boolean fields dynamically
    meta = frappe.get_meta("Vehicle Type")
    fields_to_fetch = ["container", "code", "reefer"]
    
    # Add boolean fields if they exist
    boolean_fields = ["special", "oversized", "heavy_haul", "multimodal"]
    for field in boolean_fields:
        if meta.has_field(field):
            fields_to_fetch.append(field)
    
    vehicle_details = frappe.get_value(
        "Vehicle Type",
        vehicle_type,
        fields_to_fetch,
        as_dict=True
    )
    
    if not vehicle_details:
        return {"compatible": False, "message": f"Vehicle Type {vehicle_type} not found"}
    
    compatible = True
    messages = []
    
    # Check container compatibility
    if transport_job_type == "Container":
        if not vehicle_details.container:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not container. Container job type requires a container vehicle type.")
    elif transport_job_type == "Non-Container":
        if vehicle_details.container:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is container. Non-Container job type requires a non-container vehicle type.")
    
    # Check boolean field compatibility for specific job types
    if transport_job_type == "Special":
        if not vehicle_details.reefer:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} does not have reefer capability. Special job type requires a vehicle with reefer enabled.")
        if not getattr(vehicle_details, "special", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Special. Special job type requires a vehicle type with special capability.")
    elif transport_job_type == "Oversized":
        if not getattr(vehicle_details, "oversized", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Oversized. Oversized job type requires a vehicle type with oversized capability.")
    elif transport_job_type == "Heavy Haul":
        if not getattr(vehicle_details, "heavy_haul", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Heavy Haul. Heavy Haul job type requires a vehicle type with heavy haul capability.")
    elif transport_job_type == "Multimodal":
        if not getattr(vehicle_details, "multimodal", False):
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} is not marked as Multimodal. Multimodal job type requires a vehicle type with multimodal capability.")
    
    # Check reefer requirement for other job types (only if refrigeration is actually checked)
    # Only check if refrigeration is explicitly True/1 and transport_job_type is not "Special"
    # Handle cases where refrigeration might be passed as 0, False, "0", None, etc.
    refrigeration_enabled = refrigeration in (True, 1) or (isinstance(refrigeration, str) and refrigeration == "1")
    if refrigeration_enabled and transport_job_type != "Special":
        if not vehicle_details.reefer:
            compatible = False
            messages.append(f"Vehicle Type {vehicle_details.code} does not have reefer capability. Refrigerated transport requires a vehicle with reefer enabled.")
    
    return {"compatible": compatible, "message": " ".join(messages) if messages else ""}


@frappe.whitelist()
def get_cost_estimation(transport_job_type: str, base_cost: float = 1000) -> Dict[str, Any]:
    """Get cost estimation based on transport job type."""
    if not transport_job_type or not base_cost:
        return {}
    
    factors = {
        "base_cost": base_cost,
        "surcharge_rate": 0.0,
        "surcharge_amount": 0.0,
        "total_cost": base_cost,
        "special_handling": False
    }
    
    if transport_job_type == "Heavy Haul":
        factors["surcharge_rate"] = 0.5
        factors["special_handling"] = True
    elif transport_job_type == "Oversized":
        factors["surcharge_rate"] = 0.3
        factors["special_handling"] = True
    elif transport_job_type == "Special":
        factors["surcharge_rate"] = 0.4
        factors["special_handling"] = True
    elif transport_job_type == "Multimodal":
        factors["surcharge_rate"] = 0.2
    elif transport_job_type == "Container":
        factors["surcharge_rate"] = 0.1
    else:  # Non-Container
        factors["surcharge_rate"] = 0.0
    
    factors["surcharge_amount"] = base_cost * factors["surcharge_rate"]
    factors["total_cost"] = base_cost + factors["surcharge_amount"]
    
    return factors


@frappe.whitelist()
def get_consolidation_opportunities(transport_order_name: str) -> Dict[str, Any]:
    """Get consolidation opportunities for a transport order."""
    try:
        doc = frappe.get_doc("Transport Order", transport_order_name)
        
        if not doc.get_consolidation_eligibility():
            return {"eligible": False, "reason": "Transport order not eligible for consolidation"}
        
        order_meta = frappe.get_meta("Transport Order")
        filters = {
                "transport_job_type": doc.transport_job_type,
                "load_type": doc.load_type,
                "docstatus": 1,
            "name": ["!=", doc.name],
        }

        if order_meta.has_field("company") and getattr(doc, "company", None):
            filters["company"] = doc.company

        if order_meta.has_field("branch") and getattr(doc, "branch", None):
            filters["branch"] = doc.branch

        # Find other eligible transport orders
        try:
            eligible_orders = frappe.get_all(
                "Transport Order",
                filters=filters,
            fields=["name", "customer", "booking_date", "scheduled_date"],
                limit=10,
        )
        except ProgrammingError as err:
            frappe.log_error(f"Error fetching consolidation opportunities: {err}", "Transport Order Consolidation")
            return {"eligible": False, "error": str(err)}
        
        return {
            "eligible": True,
            "current_order": doc.name,
            "job_type": doc.transport_job_type,
            "load_type": doc.load_type,
            "opportunities": eligible_orders
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting consolidation opportunities: {str(e)}")
        return {"eligible": False, "error": str(e)}


# =========================
# Copy/link helpers
# =========================
def _copy_child_rows_by_common_fields(src_doc: Document, src_table_field: str, dst_doc: Document, dst_table_field: str):
    """Copy child rows from src to dst, matching by common fieldnames only."""
    src_rows = src_doc.get(src_table_field) or []
    if not src_rows:
        return

    dst_parent_meta = frappe.get_meta(dst_doc.doctype)
    dst_tbl_df = dst_parent_meta.get_field(dst_table_field)
    if not dst_tbl_df or not dst_tbl_df.options:
        return

    dst_child_dt = dst_tbl_df.options
    dst_child_meta = frappe.get_meta(dst_child_dt)

    excluded_types = {"Section Break", "Column Break", "Tab Break", "Table", "Table MultiSelect"}
    excluded_names = {
        "name",
        "owner",
        "modified_by",
        "creation",
        "modified",
        "parent",
        "parentfield",
        "parenttype",
        "idx",
        "docstatus",
    }
    dst_fields = {
        df.fieldname
        for df in dst_child_meta.fields
        if df.fieldtype not in excluded_types and df.fieldname not in excluded_names
    }

    for s in src_rows:
        s_dict = s.as_dict()
        new_row = {fn: s_dict.get(fn) for fn in dst_fields if fn in s_dict}
        dst_doc.append(dst_table_field, new_row)


def _create_and_attach_job_legs_from_order_legs(
    order_doc: Document, job_doc: Document, order_legs_field: str, job_legs_field: str
):
    """
    Create Transport Leg docs from Transport Order Legs and attach them to Transport Job Legs.

    Copies these fields when available on the order leg:
      facility_type_from, facility_from, pick_mode, pick_address,
      facility_type_to,   facility_to,   drop_mode, drop_address

    Also sets Transport Job reference on each created Transport Leg.
    """
    order_legs = order_doc.get(order_legs_field) or []
    if not order_legs:
        return

    for ol in order_legs:
        # Validate pick_mode and drop_mode are valid Pick and Drop Mode records if set
        # Ensure values are passed through unchanged and remain valid
        pick_mode = getattr(ol, "pick_mode", None)
        drop_mode = getattr(ol, "drop_mode", None)
        
        if pick_mode and not frappe.db.exists("Pick and Drop Mode", pick_mode):
            frappe.throw(_("Invalid pick_mode '{0}' in Transport Order Leg. Must be a valid Pick and Drop Mode record.").format(pick_mode))
        
        if drop_mode and not frappe.db.exists("Pick and Drop Mode", drop_mode):
            frappe.throw(_("Invalid drop_mode '{0}' in Transport Order Leg. Must be a valid Pick and Drop Mode record.").format(drop_mode))
        
        # Create top-level Transport Leg
        leg = frappe.new_doc("Transport Leg")
        _safe_set(leg, "transport_job", job_doc.name)  # back-reference to the Job
        _safe_set(leg, "date", order_doc.scheduled_date)  # back-reference to the Job

        _safe_set(leg, "facility_type_from", getattr(ol, "facility_type_from", None))
        _safe_set(leg, "facility_from", getattr(ol, "facility_from", None))
        _safe_set(leg, "pick_mode", pick_mode)  # Use validated value
        _safe_set(leg, "pick_address", getattr(ol, "pick_address", None))

        _safe_set(leg, "facility_type_to", getattr(ol, "facility_type_to", None))
        _safe_set(leg, "facility_to", getattr(ol, "facility_to", None))
        _safe_set(leg, "drop_mode", drop_mode)  # Use validated value
        _safe_set(leg, "drop_address", getattr(ol, "drop_address", None))
        
        # Map transport details from order leg
        _safe_set(leg, "vehicle_type", getattr(ol, "vehicle_type", None))
        _safe_set(leg, "transport_job_type", getattr(ol, "transport_job_type", None))

        leg.insert(ignore_permissions=False)

        # Link into Transport Job Legs child table (denormalized snapshot for quick view/filter)
        # Pass through pick_mode and drop_mode unchanged (already validated above)
        job_doc.append(
            job_legs_field,
            {
                "transport_leg": leg.name,
                "facility_type_from": getattr(ol, "facility_type_from", None),
                "facility_from": getattr(ol, "facility_from", None),
                "pick_mode": pick_mode,  # Use validated value, passed through unchanged
                "pick_address": getattr(ol, "pick_address", None),
                "facility_type_to": getattr(ol, "facility_type_to", None),
                "facility_to": getattr(ol, "facility_to", None),
                "drop_mode": drop_mode,  # Use validated value, passed through unchanged
                "drop_address": getattr(ol, "drop_address", None),
                "vehicle_type": getattr(ol, "vehicle_type", None),
                "transport_job_type": getattr(ol, "transport_job_type", None),
            },
        )


def _safe_set(doc: Document, fieldname: str, value):
    """Set a value only if the field exists on the document."""
    if value is None:
        return
    meta = frappe.get_meta(doc.doctype)
    if meta.has_field(fieldname):
        doc.set(fieldname, value)
