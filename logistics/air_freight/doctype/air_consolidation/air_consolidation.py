import frappe
from frappe.exceptions import ValidationError
from frappe.model.document import Document
from frappe import _
from frappe.utils import cstr, flt
import json
from datetime import datetime, timedelta

from logistics.utils.consolidation_plan import (
	assert_air_consolidation_plan_requirements,
	assert_air_plan_fields_for_strict_match,
	air_shipment_allowed_on_plan,
	conflicting_submitted_air_planning_elsewhere,
	get_air_shipment_names_from_consolidation,
	get_strict_matching_air_shipment_names,
)


class AirConsolidation(Document):
    @frappe.whitelist()
    def get_dashboard_html(self):
        """Generate HTML for Dashboard tab: consolidation details, milestones, documents and header alerts."""
        try:
            from logistics.document_management.api import (
                get_dashboard_alerts_html,
                get_document_alerts_html,
            )
            from logistics.document_management.dashboard_layout import build_run_sheet_style_dashboard

            status = self.get("status") or "Draft"
            status_badge_html = f'<span class="dash-status-badge {(status or "draft").lower().replace(" ", "_")}">{frappe.utils.escape_html(status)}</span>'
            header_items = [
                ("Status", status),
                ("Consolidation Date", str(self.consolidation_date) if self.consolidation_date else "—"),
                ("Type", self.consolidation_type or "—"),
                ("Origin", self.origin_airport or "—"),
                ("Destination", self.destination_airport or "—"),
                ("Departure", str(self.departure_date) if self.departure_date else "—"),
                ("Arrival", str(self.arrival_date) if self.arrival_date else "—"),
                ("Airline", self.airline or "—"),
                ("Packages", str(self.total_packages or 0)),
                ("Weight", frappe.format_value(self.total_weight or 0, df=dict(fieldtype="Float"))),
                ("Volume", frappe.format_value(self.total_volume or 0, df=dict(fieldtype="Float"))),
            ]
            alerts_html = get_dashboard_alerts_html("Air Consolidation", self.name or "new")
            try:
                doc_alerts_html = get_document_alerts_html("Air Consolidation", self.name or "new")
            except Exception:
                doc_alerts_html = ""

            milestone_rows = list(self.get("milestones") or [])
            milestone_details = {}
            if milestone_rows:
                names = [m.milestone for m in milestone_rows if m.milestone]
                if names:
                    for lm in frappe.get_all(
                        "Logistics Milestone",
                        filters={"name": ["in", names]},
                        fields=["name", "description"],
                    ):
                        milestone_details[lm.name] = lm.description or lm.name

            cards_html = ""
            for i, m in enumerate(milestone_rows, 1):
                st = (m.status or "Planned").lower().replace(" ", "-")
                desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
                planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
                actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
                cards_html += f"""
                <div class="dash-card {st}">
                    <div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
                    <div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
                    <span class="card-badge {st}">{m.status or "Planned"}</span>
                </div>"""

            if not cards_html:
                cards_html = '<div class="text-muted">No milestones. Use Get Milestones in Milestones tab. Attached Air Shipments in Shipments tab.</div>'

            return build_run_sheet_style_dashboard(
                header_title=self.name or "Air Consolidation",
                header_subtitle="Air Consolidation",
                header_items=header_items,
                status_badge_html=status_badge_html,
                alerts_html=alerts_html,
                cards_html=cards_html,
                map_points=[],
                map_id_prefix="ac-dash-map",
                doc_alerts_html=doc_alerts_html,
                straight_line=True,
                origin_label=self.origin_airport or "—",
                destination_label=self.destination_airport or "—",
                hide_map=True,
                cards_full_width=True,
            )
        except Exception as e:
            frappe.log_error(f"Air Consolidation get_dashboard_html: {str(e)}", "Air Consolidation Dashboard")
            return "<div class='alert alert-warning'>Error loading dashboard.</div>"

    def validate(self):
        """Validate Air Consolidation document"""
        self._prevent_planning_lines_edit_when_submitted()
        self.validate_dates()
        self.validate_consolidation_data()
        self.validate_route_consistency()
        self.validate_capacity_constraints()
        self.validate_attached_jobs_compatibility()
        self.validate_jobs_not_in_multiple_consolidations()
        self.calculate_consolidation_metrics()
        self.validate_dangerous_goods_compliance()
        self.validate_accounts()
        self._validate_consolidation_planning_lines()
        assert_air_consolidation_plan_requirements(self)

    def _prevent_planning_lines_edit_when_submitted(self):
        if getattr(self.flags, "ignore_planning_lines_lock", False):
            return
        if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
            return
        if getattr(frappe.flags, "in_import", False):
            return
        if self.is_new():
            return
        if (self.air_planning_status or "Draft") != "Submitted":
            return
        prev = self.get_doc_before_save()
        if not prev:
            return

        def shipment_tuple(doc):
            return tuple(
                sorted(
                    getattr(r, "air_shipment", None)
                    for r in (doc.consolidation_planning_lines or [])
                    if getattr(r, "air_shipment", None)
                )
            )

        if shipment_tuple(prev) != shipment_tuple(self):
            frappe.throw(
                _(
                    "Planned shipments cannot be changed while planning status is Submitted. "
                    "Reset planned shipments to draft if you need to edit the list."
                ),
                title=_("Planning locked"),
            )

    def _validate_consolidation_planning_lines(self):
        rows = self.get("consolidation_planning_lines") or []
        seen = set()
        for row in rows:
            sh = row.air_shipment
            if not sh:
                continue
            if sh in seen:
                frappe.throw(_("Air Shipment {0} is duplicated in planning lines.").format(sh))
            seen.add(sh)
            ok, msg = air_shipment_allowed_on_plan(sh)
            if not ok:
                frappe.throw(msg)
            origin = frappe.db.get_value("Air Shipment", sh, "origin_port")
            dest = frappe.db.get_value("Air Shipment", sh, "destination_port")
            if self.origin_airport and origin and origin != self.origin_airport:
                frappe.throw(
                    _("Air Shipment {0} origin {1} does not match consolidation origin {2}.").format(
                        sh, origin, self.origin_airport
                    )
                )
            if self.destination_airport and dest and dest != self.destination_airport:
                frappe.throw(
                    _("Air Shipment {0} destination {1} does not match consolidation destination {2}.").format(
                        sh, dest, self.destination_airport
                    )
                )
            if (self.air_planning_status or "Draft") == "Draft":
                if conflicting_submitted_air_planning_elsewhere(
                    sh, self.name if not self.is_new() else None
                ):
                    frappe.throw(
                        _(
                            "Air Shipment {0} is already reserved on another consolidation's submitted planning."
                        ).format(sh),
                        title=_("Planning Conflict"),
                    )
    
    def before_save(self):
        """Actions before saving the document"""
        # Apply settings defaults if this is a new document
        if self.is_new():
            self.apply_settings_defaults()
        
        self.update_consolidation_status()
        self.calculate_total_charges()
        self.optimize_consolidation_ratio()
        # Job Number will be created in after_insert method
    
    def after_insert(self):
        """Create Job Number after document is inserted"""
        # Apply settings defaults if not already applied
        if not hasattr(self, '_settings_applied'):
            self.apply_settings_defaults()
        
        # Create job costing if enabled in settings
        settings = self.get_air_freight_settings()
        if settings and settings.auto_create_job_costing:
            self.create_job_number_if_needed()
        
        # Save the document to persist changes
        if self.job_number:
            self.save(ignore_permissions=True)
    
    def on_update(self):
        """Actions after document update"""
        self.update_related_air_freight_jobs()
        self.update_attached_jobs_table()
        self.send_consolidation_notifications()

    def before_submit(self):
        if not self.consolidation_packages:
            frappe.throw(_("At least one package must be added to the consolidation"))
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
        distinct_jobs = set(get_air_shipment_names_from_consolidation(self))
        for row in self.get("consolidation_planning_lines") or []:
            aj = getattr(row, "air_shipment", None)
            if aj:
                distinct_jobs.add(aj)
        if len(distinct_jobs) == 1:
            frappe.throw(
                _("An Air Consolidation must include at least two distinct Air Shipments."),
                title=_("Insufficient shipments"),
            )
        if get_air_shipment_names_from_consolidation(self) and (self.air_planning_status or "Draft") != "Submitted":
            frappe.throw(
                _("Submit the planned shipment list (Planning status) before submitting the consolidation."),
                title=_("Planning required"),
            )

    def _air_plan_route_fallback_row(self):
        """Prefer child route matching header O/D; else first route (main leg data often lives here)."""
        routes = self.get("consolidation_routes") or []
        if not routes:
            return None
        ho, hd = self.origin_airport, self.destination_airport
        for row in routes:
            ro = getattr(row, "origin_airport", None)
            rd = getattr(row, "destination_airport", None)
            if ho and hd and ro == ho and rd == hd:
                return row
        return routes[0]

    def _air_plan_match_dict(self):
        dep = self.departure_date
        airline = self.airline
        flight_number = self.flight_number
        r = self._air_plan_route_fallback_row()
        if r:
            if not dep:
                # Route table uses Date; strict match uses calendar day only (getdate on target).
                dep = getattr(r, "departure_date", None) or dep
            if not airline:
                airline = getattr(r, "airline", None)
            if not (flight_number or "").strip():
                flight_number = getattr(r, "flight_number", None)
        return {
            "company": self.company,
            "branch": self.branch,
            "origin_airport": self.origin_airport,
            "destination_airport": self.destination_airport,
            "target_departure": dep,
            "airline": airline,
            "flight_number": flight_number,
        }

    def _merged_air_plan_match_dict_from_dialog(self, filter_overrides):
        keys = (
            "company",
            "branch",
            "origin_airport",
            "destination_airport",
            "target_departure",
            "airline",
            "flight_number",
        )
        base = dict(self._air_plan_match_dict())
        o = filter_overrides or {}
        if isinstance(o, str):
            o = frappe.parse_json(o) or {}
        if not isinstance(o, dict):
            o = {}
        for key in keys:
            if key not in o:
                continue
            val = o[key]
            if val is None or (isinstance(val, str) and not str(val).strip()):
                continue
            base[key] = val
        return base

    @frappe.whitelist()
    def preview_matching_air_shipments(self, filter_overrides=None):
        """Return strict-matching shipments with eligibility for each row (no save)."""
        # Do not reload from DB: the dialog reads frm.doc (including unsaved edits). Reloading
        # would query with stale header fields while the UI still shows the user's criteria.
        if self.is_new():
            return {"error": _("Save the consolidation first.")}

        merged = self._merged_air_plan_match_dict_from_dialog(filter_overrides)
        try:
            assert_air_plan_fields_for_strict_match(merged)
        except ValidationError as e:
            return {"error": cstr(getattr(e, "message", e))}

        candidates = get_strict_matching_air_shipment_names(merged)
        present = {
            r.air_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "air_shipment", None)
        }

        rows = []
        for name in candidates:
            shipment = frappe.db.get_value(
                "Air Shipment",
                name,
                [
                    "name",
                    "job_status",
                    "origin_port",
                    "destination_port",
                    "airline",
                    "etd",
                    "company",
                    "branch",
                ],
                as_dict=True,
            ) or {}

            row = {"name": name, "job_status": shipment.get("job_status") or "", "row_type": "eligible"}
            if shipment.get("company") and shipment.get("branch"):
                row["subtitle"] = "{0} · {1}".format(
                    shipment.get("company"),
                    shipment.get("branch"),
                )
            if name in present:
                row["row_type"] = "already"
                row["origin_port"] = shipment.get("origin_port") or ""
                row["destination_port"] = shipment.get("destination_port") or ""
                row["airline"] = shipment.get("airline") or ""
                row["etd"] = shipment.get("etd")
                rows.append(row)
                continue
            ok, msg = air_shipment_allowed_on_plan(name)
            if not ok:
                row["row_type"] = "blocked"
                row["reason"] = cstr(msg)
                rows.append(row)
                continue
            if conflicting_submitted_air_planning_elsewhere(name, self.name):
                row["row_type"] = "blocked"
                row["reason"] = _("Reserved on another consolidation's submitted planning.")
                rows.append(row)
                continue
            row["origin_port"] = shipment.get("origin_port") or ""
            row["destination_port"] = shipment.get("destination_port") or ""
            row["airline"] = shipment.get("airline") or ""
            row["etd"] = shipment.get("etd")
            rows.append(row)

        banner = _("{0} candidate(s); {1} can be added").format(
            len(candidates), len([r for r in rows if r.get("row_type") == "eligible"])
        )
        return {"rows": rows, "message": banner}

    @frappe.whitelist()
    def apply_selected_air_shipments_to_planning(self, shipment_names, filter_overrides=None):
        """Append shipments chosen in the alignment dialog."""
        names = frappe.parse_json(shipment_names) if isinstance(shipment_names, str) else shipment_names
        if not names:
            frappe.throw(_("Select at least one shipment."), title=_("Nothing selected"))

        preview = self.preview_matching_air_shipments(filter_overrides)
        if isinstance(preview, dict) and preview.get("error"):
            frappe.throw(preview["error"])

        eligible = {r["name"] for r in (preview.get("rows") or []) if r.get("row_type") == "eligible"}

        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Cannot add shipments after planning is submitted."), title=_("Planning locked"))

        added, skipped = [], []
        seen = set()
        for nm in names:
            if nm in seen:
                continue
            seen.add(nm)
            if nm not in eligible:
                skipped.append(nm)
                continue
            ok, msg = air_shipment_allowed_on_plan(nm)
            if not ok:
                frappe.throw(cstr(msg))
            if conflicting_submitted_air_planning_elsewhere(nm, self.name):
                frappe.throw(_("Air Shipment {0} cannot be reserved on this consolidation.").format(nm))
            self.append("consolidation_planning_lines", {"air_shipment": nm})
            added.append(nm)

        self.save()
        msg = _("{0} added").format(len(added))
        if skipped:
            msg += " · " + _("{0} not applied (criteria changed or not eligible).").format(len(skipped))
        return {"added": added, "skipped": skipped, "message": msg}

    @frappe.whitelist()
    def fetch_matching_air_shipments(self):
        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Cannot fetch shipments after planning is submitted."), title=_("Planning locked"))
        if self.is_new():
            frappe.throw(_("Save the consolidation before fetching shipments."), title=_("Save required"))
        assert_air_plan_fields_for_strict_match(self._air_plan_match_dict())
        candidates = get_strict_matching_air_shipment_names(self._air_plan_match_dict())
        present = {
            r.air_shipment
            for r in (self.get("consolidation_planning_lines") or [])
            if getattr(r, "air_shipment", None)
        }
        added, already_present, skipped = [], [], []
        for name in candidates:
            if name in present:
                already_present.append(name)
                continue
            ok, msg = air_shipment_allowed_on_plan(name)
            if not ok:
                skipped.append({"shipment": name, "reason": msg})
                continue
            if conflicting_submitted_air_planning_elsewhere(name, self.name):
                skipped.append(
                    {
                        "shipment": name,
                        "reason": _("Reserved on another consolidation's submitted planning."),
                    }
                )
                continue
            self.append("consolidation_planning_lines", {"air_shipment": name})
            added.append(name)
            present.add(name)
        self.save()
        return {"added": added, "already_present": already_present, "skipped": skipped}

    @frappe.whitelist()
    def submit_air_planning(self):
        self.reload()
        if (self.air_planning_status or "Draft") == "Submitted":
            frappe.throw(_("Planning is already submitted."), title=_("Already submitted"))
        if not self.get("consolidation_planning_lines"):
            frappe.throw(
                _("Add at least one shipment to planning before submitting."), title=_("No Lines")
            )
        self.air_planning_status = "Submitted"
        if not self.planning_owner:
            self.planning_owner = frappe.session.user
        self.save()
        return self.air_planning_status

    @frappe.whitelist()
    def cancel_air_planning_submit(self):
        self.reload()
        if (self.air_planning_status or "Draft") != "Submitted":
            frappe.throw(_("Planning is not submitted."), title=_("Not submitted"))
        if self.docstatus != 0:
            frappe.throw(
                _("Cancel planning only while the consolidation is still draft (not submitted)."),
                title=_("Not allowed"),
            )
        if get_air_shipment_names_from_consolidation(self):
            frappe.throw(
                _("Remove packages that reference air shipments before cancelling planning."),
                title=_("Cargo linked"),
            )
        self.air_planning_status = "Draft"
        self.planning_owner = None
        self.save()
        return self.air_planning_status
    
    def validate_consolidation_data(self):
        """Validate consolidation data integrity (packages required only on submit; see before_submit)."""
        if not self.consolidation_routes:
            frappe.throw(_("At least one route must be defined for the consolidation"))
        
        # Date validation is handled in validate_dates() method
    
    def validate_route_consistency(self):
        """Validate route consistency and connectivity"""
        if len(self.consolidation_routes) > 1:
            for i, route in enumerate(self.consolidation_routes):
                if i > 0:
                    # Check if destination of previous route matches origin of current route
                    prev_route = self.consolidation_routes[i-1]
                    if prev_route.destination_airport != route.origin_airport:
                        frappe.throw(
                            _("Route {0}: Origin airport must match destination of previous route").format(i + 1)
                        )
    
    def validate_capacity_constraints(self):
        """Validate capacity constraints for all routes"""
        for i, route in enumerate(self.consolidation_routes, start=1):
            if route.cargo_capacity_kg and self.total_weight > route.cargo_capacity_kg:
                frappe.throw(_("Route {0}: Total weight exceeds cargo capacity").format(i))

            if route.cargo_capacity_volume and self.total_volume > route.cargo_capacity_volume:
                frappe.throw(_("Route {0}: Total volume exceeds cargo capacity").format(i))
    
    def validate_attached_jobs_compatibility(self):
        """Validate that attached Air Shipments are compatible for consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Air Shipments
        attached_jobs = []
        for package in self.consolidation_packages:
            if package.air_freight_job:
                attached_jobs.append(package.air_freight_job)
        
        if not attached_jobs:
            return
        
        # Get job details
        jobs_data = frappe.get_all(
            "Air Shipment",
            filters={"name": ["in", attached_jobs]},
            fields=["name", "origin_port", "destination_port", "service_level", "contains_dangerous_goods", "direction"]
        )
        
        if not jobs_data:
            return
        
        # Check all jobs have same origin and destination airports
        first_job = jobs_data[0]
        for job in jobs_data[1:]:
            if job.origin_port != first_job.origin_port:
                frappe.throw(
                    _("Air Shipment {0} has different origin port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        job.name, job.origin_port, first_job.origin_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            if job.destination_port != first_job.destination_port:
                frappe.throw(
                    _("Air Shipment {0} has different destination port ({1}) than other shipments ({2}). All shipments in a consolidation must have the same origin and destination.").format(
                        job.name, job.destination_port, first_job.destination_port
                    ),
                    title=_("Consolidation Compatibility Error")
                )
            
            # Check direction compatibility
            if job.direction != first_job.direction:
                frappe.throw(
                    _("Air Shipment {0} has different direction ({1}) than other shipments ({2}). All shipments in a consolidation must have the same direction.").format(
                        job.name, job.direction, first_job.direction
                    ),
                    title=_("Consolidation Compatibility Error")
                )
    
    def validate_jobs_not_in_multiple_consolidations(self):
        """Validate that Air Shipments are not already in another consolidation"""
        if not self.consolidation_packages:
            return
        
        # Get all attached Air Shipments
        attached_jobs = []
        for package in self.consolidation_packages:
            if package.air_freight_job:
                attached_jobs.append(package.air_freight_job)
        
        if not attached_jobs:
            return
        
        # Check if any of these jobs are already in another consolidation
        existing_consolidations = frappe.get_all(
            "Air Consolidation Packages",
            filters={
                "air_freight_job": ["in", attached_jobs],
                "parent": ["!=", self.name]
            },
            fields=["parent", "air_freight_job"],
            group_by="air_freight_job"
        )
        
        if existing_consolidations:
            for consolidation in existing_consolidations:
                frappe.throw(
                    _("Air Shipment {0} is already included in consolidation {1}. A shipment can only be in one consolidation at a time.").format(
                        consolidation.air_freight_job, consolidation.parent
                    ),
                    title=_("Consolidation Conflict Error")
                )
    
    def calculate_consolidation_metrics(self):
        """Calculate consolidation metrics"""
        if self.consolidation_packages:
            # Calculate totals
            self.total_packages = sum(package.package_count for package in self.consolidation_packages)
            self.total_weight = sum(package.package_weight for package in self.consolidation_packages)
            self.total_volume = sum(package.package_volume or 0 for package in self.consolidation_packages)
            
            from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

            settings = self.get_air_freight_settings()
            volume_to_weight_factor = IATA_VOLUMETRIC_DENSITY_KG_M3
            chargeable_weight_calculation = "Higher of Both"  # Default
            
            if settings:
                volume_to_weight_factor = settings.volume_to_weight_factor or IATA_VOLUMETRIC_DENSITY_KG_M3
                chargeable_weight_calculation = settings.chargeable_weight_calculation or "Higher of Both"
            
            # Calculate chargeable weight based on settings
            volume_weight = self.total_volume * volume_to_weight_factor
            
            if chargeable_weight_calculation == "Actual Weight":
                self.chargeable_weight = self.total_weight
            elif chargeable_weight_calculation == "Volume Weight":
                self.chargeable_weight = volume_weight
            else:  # Higher of Both (default)
                self.chargeable_weight = max(self.total_weight, volume_weight)
            
            # Calculate consolidation ratio
            if self.total_weight > 0:
                self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
    
    def validate_dangerous_goods_compliance(self):
        """Validate dangerous goods compliance for consolidation"""
        dg_packages = [p for p in self.consolidation_packages if p.contains_dangerous_goods]
        
        if dg_packages:
            # Check if all routes allow dangerous goods
            for i, route in enumerate(self.consolidation_routes, start=1):
                if not route.dangerous_goods_allowed:
                    frappe.throw(
                        _("Route {0} does not allow dangerous goods, but consolidation contains DG packages").format(i)
                    )
            
            # Validate DG segregation requirements
            self.validate_dg_segregation(dg_packages)
    
    def validate_dg_segregation(self, dg_packages):
        """Validate dangerous goods segregation requirements"""
        dg_classes = [p.dg_class for p in dg_packages if p.dg_class]
        
        # Check for incompatible DG classes
        incompatible_pairs = [
            ("1", "2"),  # Explosives with gases
            ("3", "5"),  # Flammable liquids with oxidizing substances
            ("4", "5"),  # Flammable solids with oxidizing substances
        ]
        
        for class1, class2 in incompatible_pairs:
            if class1 in dg_classes and class2 in dg_classes:
                frappe.throw(_("Incompatible dangerous goods classes {0} and {1} cannot be consolidated together".format(class1, class2)))
    
    def update_consolidation_status(self):
        """Update consolidation status based on current data"""
        if self.status == "Draft":
            if self.consolidation_packages and self.consolidation_routes:
                self.status = "Planning"
        elif self.status == "Planning":
            if self.master_awb:
                self.status = "Ready for Departure"
        elif self.status == "Ready for Departure":
            if self.departure_date and self.departure_date <= frappe.utils.now():
                self.status = "In Transit"
        elif self.status == "In Transit":
            if self.arrival_date and self.arrival_date <= frappe.utils.now():
                self.status = "Delivered"
    
    def calculate_total_charges(self):
        """Calculate total charges for the consolidation"""
        total_charges = 0
        
        for charge in self.consolidation_charges:
            if charge.revenue_calculation_method == "Per Unit":
                ut = getattr(charge, "unit_type", None)
                if ut == "Weight":
                    charge.base_amount = charge.rate * self.chargeable_weight
                elif ut == "Chargeable Weight":
                    cq = flt(self.chargeable_weight or 0)
                    if cq <= 0:
                        cq = flt(self.total_weight or 0)
                    charge.base_amount = charge.rate * cq
                elif ut == "Volume":
                    charge.base_amount = charge.rate * self.total_volume
                elif ut in ("Package", "Piece"):
                    charge.base_amount = charge.rate * (self.total_packages or 0)
                else:
                    charge.base_amount = charge.rate * (charge.quantity or 0)
            elif charge.revenue_calculation_method == "Flat Rate":
                charge.base_amount = charge.rate
            elif charge.revenue_calculation_method == "Percentage":
                charge.base_amount = charge.rate * (self.chargeable_weight * 0.01)
            
            # Calculate discount
            if charge.discount_percentage:
                charge.discount_amount = charge.base_amount * (charge.discount_percentage / 100)
            
            # Calculate total amount
            charge.total_amount = charge.base_amount - charge.discount_amount + charge.surcharge_amount
            
            total_charges += charge.total_amount
        
        # Calculate cost per kg
        if self.chargeable_weight > 0:
            self.cost_per_kg = total_charges / self.chargeable_weight
    
    def optimize_consolidation_ratio(self):
        """Optimize consolidation ratio for better space utilization"""
        if self.total_weight > 0 and self.total_volume > 0:
            # Get settings for volume to weight factor
            from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

            settings = self.get_air_freight_settings()
            standard_density = IATA_VOLUMETRIC_DENSITY_KG_M3
            
            if settings:
                standard_density = settings.volume_to_weight_factor or IATA_VOLUMETRIC_DENSITY_KG_M3
            
            # Calculate density
            density = self.total_weight / self.total_volume
            
            if density < standard_density:
                # Low density cargo - volume weight applies
                self.consolidation_ratio = (self.chargeable_weight / self.total_weight) * 100
            else:
                # High density cargo - actual weight applies
                self.consolidation_ratio = 100
    
    def update_related_air_freight_jobs(self):
        """Update related Air Shipments with consolidation information"""
        for package in self.consolidation_packages:
            if package.air_freight_job:
                # Update the Air Shipment with consolidation reference
                frappe.db.set_value("Air Shipment", package.air_freight_job, {
                    "consolidation_reference": self.name,
                    "consolidation_status": package.consolidation_status
                })
    
    def send_consolidation_notifications(self):
        """Send notifications for consolidation status changes"""
        if self.status in ["Ready for Departure", "In Transit", "Delivered"]:
            # Get all related customers
            customers = set()
            for package in self.consolidation_packages:
                if package.shipper:
                    customers.add(package.shipper)
                if package.consignee:
                    customers.add(package.consignee)
            
            # Send notifications
            for customer in customers:
                self.send_customer_notification(customer)
    
    def send_customer_notification(self, customer):
        """Send notification to customer about consolidation status"""
        subject = f"Consolidation {self.name} - Status Update"
        message = f"""
        Your consolidation {self.name} status has been updated to: {self.status}
        
        Route: {self.origin_airport} → {self.destination_airport}
        Departure: {self.departure_date}
        Arrival: {self.arrival_date}
        
        Please contact us for any questions.
        """
        
        frappe.sendmail(
            recipients=[customer],
            subject=subject,
            message=message
        )
    
    @frappe.whitelist()
    def add_package_from_job(self, air_freight_job):
        """Add package from Air Shipment to consolidation"""
        job = frappe.get_doc("Air Shipment", air_freight_job)
        
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0
        package.package_volume = getattr(job, "total_volume", None) or getattr(job, "volume", None) or 0
        package.commodity = job.description
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        self.save()
        return package
    
    @frappe.whitelist()
    def optimize_route_selection(self):
        """Optimize route selection based on cost and time"""
        if not self.consolidation_routes:
            return
        
        # Calculate cost and time for each route
        route_scores = []
        for route in self.consolidation_routes:
            score = self.calculate_route_score(route)
            route_scores.append((route, score))
        
        # Sort by score (lower is better)
        route_scores.sort(key=lambda x: x[1])

        # Child row order follows idx (same pattern as Sea Consolidation Routes without route_sequence)
        for i, (route, score) in enumerate(route_scores, start=1):
            route.idx = i

        self.save()
        return route_scores
    
    def calculate_route_score(self, route):
        """Calculate optimization score for a route"""
        # Factors: cost, time, capacity utilization
        cost_factor = route.total_cost_per_kg or 0
        time_factor = route.transit_time_hours or 0
        capacity_factor = 1 - (route.utilization_percentage or 0) / 100
        
        # Weighted score (lower is better)
        score = (cost_factor * 0.5) + (time_factor * 0.3) + (capacity_factor * 0.2)
        return score
    
    @frappe.whitelist()
    def generate_consolidation_report(self):
        """Generate consolidation report"""
        report_data = {
            "consolidation_id": self.name,
            "status": self.status,
            "total_packages": self.total_packages,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "chargeable_weight": self.chargeable_weight,
            "consolidation_ratio": self.consolidation_ratio,
            "cost_per_kg": self.cost_per_kg,
            "routes": [],
            "packages": []
        }
        
        # Add route information (sequence = row order in grid)
        for seq, route in enumerate(self.consolidation_routes, start=1):
            report_data["routes"].append({
                "sequence": seq,
                "origin": route.origin_airport,
                "destination": route.destination_airport,
                "airline": route.airline,
                "flight_number": route.flight_number,
                "departure": route.departure_date,
                "arrival": route.arrival_date,
                "status": route.route_status
            })
        
        # Add package information
        for package in self.consolidation_packages:
            report_data["packages"].append({
                "reference": package.package_reference,
                "air_freight_job": package.air_freight_job,
                "shipper": package.shipper,
                "consignee": package.consignee,
                "weight": package.package_weight,
                "volume": package.package_volume,
                "status": package.consolidation_status
            })
        
        return report_data
    
    @frappe.whitelist()
    def check_capacity_availability(self):
        """Check capacity availability for all routes"""
        capacity_info = []
        
        for seq, route in enumerate(self.consolidation_routes, start=1):
            available_weight = route.available_capacity_kg or 0
            available_volume = route.available_capacity_volume or 0
            
            weight_utilization = (self.total_weight / available_weight * 100) if available_weight > 0 else 0
            volume_utilization = (self.total_volume / available_volume * 100) if available_volume > 0 else 0
            
            capacity_info.append({
                "sequence": seq,
                "available_weight": available_weight,
                "available_volume": available_volume,
                "weight_utilization": weight_utilization,
                "volume_utilization": volume_utilization,
                "status": "Available" if weight_utilization < 100 and volume_utilization < 100 else "Full"
            })
        
        return capacity_info
    
    @frappe.whitelist()
    def calculate_cost_breakdown(self):
        """Calculate detailed cost breakdown for consolidation"""
        cost_breakdown = {
            "total_cost": 0,
            "cost_per_kg": 0,
            "charges": []
        }
        
        for charge in self.consolidation_charges:
            charge_info = {
                "type": charge.charge_type,
                "category": charge.charge_category,
                "basis": charge.revenue_calculation_method,
                "rate": charge.rate,
                "quantity": charge.quantity,
                "base_amount": charge.base_amount,
                "discount": charge.discount_amount,
                "surcharge": charge.surcharge_amount,
                "total": charge.total_amount
            }
            cost_breakdown["charges"].append(charge_info)
            cost_breakdown["total_cost"] += charge.total_amount
        
        if self.chargeable_weight > 0:
            cost_breakdown["cost_per_kg"] = cost_breakdown["total_cost"] / self.chargeable_weight
        
        return cost_breakdown
    
    def update_attached_jobs_table(self):
        """Update the virtual child table with attached Air Shipments"""
        # Clear existing attached jobs
        self.attached_air_freight_jobs = []
        
        # Get all Air Shipments from consolidation packages
        job_ids = [package.air_freight_job for package in self.consolidation_packages if package.air_freight_job]
        
        for i, job_id in enumerate(job_ids):
            job = frappe.get_doc("Air Shipment", job_id)
            
            # Create attached job entry
            attached_job = self.append("attached_air_freight_jobs", {})
            attached_job.air_freight_job = job_id
            attached_job.job_status = "Submitted" if job.docstatus == 1 else "Cancelled" if job.docstatus == 2 else "Draft"
            attached_job.booking_date = job.booking_date
            attached_job.shipper = job.shipper
            attached_job.consignee = job.consignee
            attached_job.origin_port = job.origin_port
            attached_job.destination_port = job.destination_port
            attached_job.weight = getattr(job, "total_weight", None) or job.weight
            attached_job.volume = getattr(job, "total_volume", None) or job.volume
            attached_job.packs = job.packs
            attached_job.value = getattr(job, "goods_value", None) or 0
            attached_job.currency = getattr(job, "billing_currency", None) or frappe.get_cached_value("Company", job.company, "default_currency") if job.company else None
            attached_job.incoterm = job.incoterm
            attached_job.contains_dangerous_goods = job.contains_dangerous_goods or 0
            attached_job.dg_compliance_status = job.dg_compliance_status
            attached_job.dg_declaration_complete = job.dg_declaration_complete
            attached_job.consolidation_status = "Pending"
            attached_job.position_in_consolidation = i + 1
            
            # Calculate cost allocation
            if self.total_weight > 0:
                job_weight = getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0
                attached_job.cost_allocation_percentage = (job_weight / self.total_weight) * 100
            else:
                attached_job.cost_allocation_percentage = 0
    
    @frappe.whitelist()
    def add_air_freight_job(self, air_freight_job):
        """Add an Air Shipment to the consolidation"""
        # Check if job is already in consolidation
        existing_package = frappe.db.exists("Air Consolidation Packages", {
            "air_freight_job": air_freight_job,
            "parent": self.name
        })
        
        if existing_package:
            frappe.throw(_("This Air Shipment is already included in this consolidation"))
        
        # Validate house type: only consolidation types can be added (not Standard House or Break Bulk)
        job = frappe.get_doc("Air Shipment", air_freight_job)
        allowed = ("Co-load Master", "Blind Co-load Master", "Co-load House", "Buyer's Consol Lead", "Shipper's Consol Lead")
        if job.house_type not in allowed:
            frappe.throw(_(
                "Air Shipment with House Type '{0}' cannot be added to consolidation. "
                "Only Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, or Shipper's Consol Lead are allowed."
            ).format(job.house_type or "Standard House"))
        
        # Validate origin and destination match consolidation header
        if self.origin_airport and job.origin_port != self.origin_airport:
            frappe.throw(_(
                "Air Shipment {0} origin port ({1}) does not match consolidation origin ({2})."
            ).format(air_freight_job, job.origin_port or "-", self.origin_airport))
        if self.destination_airport and job.destination_port != self.destination_airport:
            frappe.throw(_(
                "Air Shipment {0} destination port ({1}) does not match consolidation destination ({2})."
            ).format(air_freight_job, job.destination_port or "-", self.destination_airport))
        
        # Add package to consolidation
        package = self.append("consolidation_packages", {})
        package.air_freight_job = air_freight_job
        
        # Get job details (job already fetched above for house_type validation)
        package.shipper = job.shipper
        package.consignee = job.consignee
        package.package_type = "Box"  # Default, can be updated
        package.package_count = job.packs or 1
        package.package_weight = getattr(job, "total_weight", None) or getattr(job, "weight", None) or 0
        package.package_volume = getattr(job, "total_volume", None) or getattr(job, "volume", None) or 0
        package.commodity = job.description
        package.contains_dangerous_goods = job.contains_dangerous_goods or 0
        
        # Update the attached jobs table
        self.update_attached_jobs_table()
        
        self.save()
        return package
    
    @frappe.whitelist()
    def remove_air_freight_job(self, air_freight_job):
        """Remove an Air Shipment from the consolidation"""
        # Remove from consolidation packages
        packages_to_remove = []
        for package in self.consolidation_packages:
            if package.air_freight_job == air_freight_job:
                packages_to_remove.append(package)
        
        for package in packages_to_remove:
            self.remove(package)
        
        # Update the attached jobs table
        self.update_attached_jobs_table()
        
        # Clear consolidation reference from the job
        frappe.db.set_value("Air Shipment", air_freight_job, {
            "consolidation_reference": None,
            "consolidation_status": None
        })
        
        self.save()
        return True
    
    @frappe.whitelist()
    def get_consolidation_summary(self):
        """Get comprehensive consolidation summary"""
        summary = {
            "consolidation_id": self.name,
            "status": self.status,
            "consolidation_type": self.consolidation_type,
            "route": f"{self.origin_airport} → {self.destination_airport}",
            "departure": self.departure_date,
            "arrival": self.arrival_date,
            "airline": self.airline,
            "flight_number": self.flight_number,
            "total_jobs": len(self.attached_air_freight_jobs),
            "total_packages": self.total_packages,
            "total_weight": self.total_weight,
            "total_volume": self.total_volume,
            "chargeable_weight": self.chargeable_weight,
            "consolidation_ratio": self.consolidation_ratio,
            "cost_per_kg": self.cost_per_kg,
            "attached_jobs": [],
            "routes": [],
            "charges": []
        }
        
        # Add attached jobs information
        for job in self.attached_air_freight_jobs:
            summary["attached_jobs"].append({
                "air_freight_job": job.air_freight_job,
                "shipper": job.shipper,
                "consignee": job.consignee,
                "route": f"{job.origin_port} → {job.destination_port}",
                "weight": getattr(job, "total_weight", None) or job.weight,
                "volume": getattr(job, "total_volume", None) or job.volume,
                "value": job.value,
                "currency": job.currency,
                "dangerous_goods": job.contains_dangerous_goods,
                "dg_status": job.dg_compliance_status,
                "consolidation_status": job.consolidation_status,
                "cost_allocation": job.cost_allocation_percentage
            })
        
        # Add route information
        for seq, route in enumerate(self.consolidation_routes, start=1):
            summary["routes"].append({
                "sequence": seq,
                "origin": route.origin_airport,
                "destination": route.destination_airport,
                "airline": route.airline,
                "flight_number": route.flight_number,
                "departure": route.departure_date,
                "arrival": route.arrival_date,
                "status": route.route_status,
                "capacity_kg": route.cargo_capacity_kg,
                "capacity_volume": route.cargo_capacity_volume,
                "utilization": route.utilization_percentage
            })
        
        # Add charges information
        for charge in self.consolidation_charges:
            summary["charges"].append({
                "type": charge.charge_type,
                "category": charge.charge_category,
                "basis": charge.revenue_calculation_method,
                "rate": charge.rate,
                "total_amount": charge.total_amount,
                "status": charge.charge_status
            })
        
        return summary
    
    def validate_dates(self):
        """Validate date fields"""
        # Validate departure date is before arrival date
        if self.departure_date and self.arrival_date:
            if self.departure_date >= self.arrival_date:
                frappe.throw(_("Departure date must be before arrival date"), 
                    title=_("Date Validation Error"))
        
        # Warn if consolidation date is in the future
        if self.consolidation_date:
            from frappe.utils import getdate, today
            if getdate(self.consolidation_date) > getdate(today()):
                frappe.msgprint(_("Consolidation date is in the future. Please verify this is correct."), 
                    indicator="orange", title=_("Date Warning"))
    
    def validate_accounts(self):
        """Validate accounting fields"""
        if not self.company:
            frappe.throw(_("Company is required"), title=_("Validation Error"))
        
        # Validate cost center belongs to company
        if self.cost_center:
            cost_center_company = frappe.get_cached_value("Cost Center", self.cost_center, "company")
            if cost_center_company and cost_center_company != self.company:
                frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
                    self.cost_center, self.company), title=_("Validation Error"))
        
        # Validate profit center belongs to company
        if self.profit_center:
            profit_center_company = frappe.get_cached_value("Profit Center", self.profit_center, "company")
            if profit_center_company and profit_center_company != self.company:
                frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
                    self.profit_center, self.company), title=_("Validation Error"))
        
        # Validate branch belongs to company
        if self.branch:
            branch_company = frappe.get_cached_value("Branch", self.branch, "company")
            if branch_company and branch_company != self.company:
                frappe.throw(_("Branch {0} does not belong to Company {1}").format(
                    self.branch, self.company), title=_("Validation Error"))
    
    def get_air_freight_settings(self):
        """Get Air Freight Settings for the company"""
        if not self.company:
            return None
        
        try:
            from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings
            return AirFreightSettings.get_settings(self.company)
        except Exception as e:
            frappe.log_error(f"Error getting Air Freight Settings: {str(e)}", "Air Consolidation - Get Settings")
            return None
    
    def apply_settings_defaults(self):
        """Apply default values from Air Freight Settings"""
        if hasattr(self, '_settings_applied'):
            return
        
        settings = self.get_air_freight_settings()
        if not settings:
            return
        
        # Apply general settings
        if not self.branch and settings.default_branch:
            self.branch = settings.default_branch
        if not self.cost_center and settings.default_cost_center:
            self.cost_center = settings.default_cost_center
        if not self.profit_center and settings.default_profit_center:
            self.profit_center = settings.default_profit_center
        
        # Apply consolidation settings
        if not self.consolidation_type and settings.default_consolidation_type:
            self.consolidation_type = settings.default_consolidation_type
        
        # Mark as applied
        self._settings_applied = True
    
    def create_job_number_if_needed(self):
        """Create Job Number when document is first saved"""
        # Check settings for auto-create job costing
        settings = self.get_air_freight_settings()
        if settings and not settings.auto_create_job_costing:
            return
        
        # Only create if job_number is not set
        if not self.job_number:
            # Check if this is the first save (no existing Job Number)
            existing_job_ref = frappe.db.get_value("Job Number", {
                "job_type": "Air Consolidation",
                "job_no": self.name
            })
            
            if not existing_job_ref:
                # Create Job Number
                job_ref = frappe.new_doc("Job Number")
                job_ref.job_type = "Air Consolidation"
                job_ref.job_no = self.name
                job_ref.company = self.company
                job_ref.branch = self.branch
                job_ref.cost_center = self.cost_center
                job_ref.profit_center = self.profit_center
                # Leave recognition_date blank - will be filled in separate function
                # Use air consolidation's consolidation_date instead
                job_ref.job_open_date = self.consolidation_date
                job_ref.insert(ignore_permissions=True)
                
                # Set the job_number field
                self.job_number = job_ref.name
                
                frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))
