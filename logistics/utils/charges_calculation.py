# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Centralized charge calculation for Air, Sea, Transport, and Declaration charges.

Follows the Sales Quote charge calculation pattern using RateCalculationEngine.
Supports Weight Break, Qty Break, and Percentage Break methods via Sales Quote break tables.
Unit Breaks (checkbox) tier rates by charge row unit_type via Charge Unit Break (#1126).
Uses calculation_method and unit_type for engine; legacy values (e.g. Per kg) are normalized via mapping.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt
from typing import Any, Dict, List, Optional, Tuple

from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage
from logistics.utils.rate_calculation_engine import RateCalculationEngine
from logistics.utils.service_role_rules import (
    get_main_service_name,
    get_main_service_type,
    get_service_role,
    SERVICE_ROLE_LINKED,
)

# During parent Document.validate(), child rows may run validate() before the DB row reflects new totals.
# Register the in-memory parent so charge math uses fresh aggregates (weight, chargeable, volume, …).
_CHARGE_RESOLUTION_PARENT_KEY = "_logistics_charge_resolution_parent"


def register_charge_resolution_parent(doc: Any) -> None:
    """Call at start of operational parent validate(); pair with clear_charge_resolution_parent in finally."""
    if not doc or not getattr(doc, "doctype", None) or not getattr(doc, "name", None):
        return
    if str(doc.name).startswith("new-") or doc.name in ("new", ""):
        return
    cache = getattr(frappe.local, _CHARGE_RESOLUTION_PARENT_KEY, None)
    if cache is None:
        cache = {}
        setattr(frappe.local, _CHARGE_RESOLUTION_PARENT_KEY, cache)
    cache[(doc.doctype, doc.name)] = doc


def clear_charge_resolution_parent(doc: Any) -> None:
    """Call in finally after parent validate()."""
    if not doc or not getattr(doc, "doctype", None) or not getattr(doc, "name", None):
        return
    cache = getattr(frappe.local, _CHARGE_RESOLUTION_PARENT_KEY, None)
    if not cache:
        return
    cache.pop((doc.doctype, doc.name), None)
    if not cache:
        try:
            delattr(frappe.local, _CHARGE_RESOLUTION_PARENT_KEY)
        except AttributeError:
            pass


# Field mapping: charge doctypes use revenue_calculation_method (revenue) and cost_calculation_method (cost)
REVENUE_METHOD_FIELDS = ("revenue_calculation_method", "calculation_method")  # calculation_method for backward compat
RATE_FIELDS = ("unit_rate",)

# Map legacy/display values (e.g. "Per kg", "Per m³") to engine calculation_method + unit_type
METHOD_TO_ENGINE = {
    "Per kg": ("Per Unit", "Weight"),
    "Per m³": ("Per Unit", "Volume"),
    "Per m3": ("Per Unit", "Volume"),
    "Per package": ("Per Unit", "Package"),
    "Per piece": ("Per Unit", "Piece"),
    "Per shipment": ("Flat Rate", None),
    "Fixed amount": ("Flat Rate", None),
    "Flat rate": ("Flat Rate", None),
    "Weight Break": ("Weight Break", "Weight"),
    "Qty Break": ("Qty Break", "Piece"),
    "Percentage Break": ("Percentage Break", "Value"),
    "Per Day": ("Per Unit", "Day"),
    "Per TEU": ("Per Unit", "TEU"),
    "Per container": ("Per Unit", "Container"),
    "Per Container": ("Per Unit", "Container"),
    "Other": ("Flat Rate", None),
}
UNIT_TYPE_FIELDS = ("unit_type",)
COST_METHOD_FIELDS = ("cost_calculation_method",)
COST_RATE_FIELDS = ("unit_cost",)
COST_UNIT_TYPE_FIELDS = ("cost_unit_type",)

# Parent doctype -> quantity field mapping for actual data extraction
PARENT_QUANTITY_FIELDS = {
    "Sales Quote": ("weight", "volume", "chargeable", "total_pieces"),
    "Air Booking": ("total_weight", "chargeable_weight", "total_volume", "total_pieces"),
    "Air Shipment": ("total_weight", "chargeable_weight", "total_volume", "total_pieces"),
    "Sea Booking": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Shipment": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Consolidation": ("total_weight", "chargeable_weight", "total_volume", "total_packages", "total_teu", "total_containers"),
    "Air Consolidation": ("total_weight", "chargeable_weight", "total_volume", "total_packages", "total_teu", "total_containers"),
    "Declaration": ("total_weight", "total_volume", "total_pieces"),
    "Declaration Order": ("total_weight", "total_volume", "total_pieces"),
    "Transport Order": ("total_weight", "total_volume", "total_distance", "total_pieces"),
    "Transport Job": ("total_weight", "total_volume", "total_distance", "total_pieces"),
    "Warehouse Job": ("total_weight", "total_volume", "total_pieces"),
    # Programme header has no cargo totals; charge math uses flat-rate / tariff context (quantities default to 0).
    "Special Project": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Docket": ("total_weight", "chargeable", "total_volume", "total_packages"),
}

# Allowed keys for client-supplied parent snapshot (calculate_charge_row); blocks arbitrary setattr.
CHARGE_PARENT_OVERRIDE_ALLOWLIST = frozenset(
    {
        "weight",
        "volume",
        "chargeable",
        "chargeable_weight",
        "pieces",
        "total_weight",
        "total_volume",
        "total_pieces",
        "total_packages",
        "total_distance",
        "distance",
        "total_teu",
        "teu",
    "total_containers",
    "total_handling_units",
    "total_operation_time",
    "operation_time",
        "transport_weight",
        "transport_volume",
        "sea_weight",
        "sea_volume",
        "air_weight",
        "air_volume",
    }
)


def _apply_charge_parent_overrides(parent_doc: Any, parent_overrides: Any) -> None:
    """Merge JSON snapshot from desk (unsaved header totals) onto loaded parent for charge math."""
    if not parent_doc or not parent_overrides:
        return
    if isinstance(parent_overrides, str):
        try:
            parent_overrides = json.loads(parent_overrides)
        except Exception:
            return
    if not isinstance(parent_overrides, dict):
        return
    for key, val in parent_overrides.items():
        if key not in CHARGE_PARENT_OVERRIDE_ALLOWLIST or val is None:
            continue
        try:
            setattr(parent_doc, key, val)
        except Exception:
            pass


def _get_field(doc: Any, *field_names: str, default=None):
    """Get first non-empty value from doc for given field names.

    For Frappe Documents, names not declared in the doctype meta are skipped so
    orphan DB columns left over from a rename (e.g. legacy ``unit_rate`` column
    on ``Transport Job Charges`` after the field was renamed to ``rate``) cannot
    poison the lookup by returning a default ``0`` / ``0.0`` ahead of the real
    field. dicts and ``frappe._dict`` snapshots (no doctype/meta) keep the old
    "first non-empty value" semantics.
    """
    meta = None
    doctype = getattr(doc, "doctype", None) if doc is not None else None
    if doctype:
        try:
            meta = frappe.get_meta(doctype)
        except Exception:
            meta = None
    for name in field_names:
        if meta is not None and not meta.has_field(name):
            continue
        val = getattr(doc, name, None)
        if val is not None and val != "":
            return val
    return default


def _sum_distance_from_legs(parent_doc: Any) -> float:
    """Sum distance from legs/routing_legs when parent has no total_distance field."""
    total = 0.0
    legs = (
        getattr(parent_doc, "legs", None)
        or getattr(parent_doc, "routing_legs", None)
        or []
    )
    for leg in legs:
        val = _get_field(
            leg,
            "distance_km", "actual_distance_km", "route_distance_km",
            "distance", "total_distance"
        )
        if val is not None and val != "":
            total += flt(val)
        else:
            # Transport Job Legs links to Transport Leg - fetch distance from linked doc
            transport_leg = getattr(leg, "transport_leg", None)
            if transport_leg:
                try:
                    tl = frappe.db.get_value(
                        "Transport Leg",
                        transport_leg,
                        ["actual_distance_km", "distance_km", "route_distance_km"],
                        as_dict=True,
                    )
                    if tl:
                        val = tl.get("actual_distance_km") or tl.get("distance_km") or tl.get("route_distance_km")
                        if val is not None:
                            total += flt(val)
                except Exception:
                    pass
    return total


def get_charge_bill_to_customers(charge: Any) -> List[str]:
    """
    Return list of Customer names/IDs this charge is billable to.
    One charge item, one Bill To only (single Link).
    """
    bill_to = getattr(charge, "bill_to", None)
    if bill_to:
        return [bill_to]
    return []


_CUSTOMS_PARENT_DOCTYPES = frozenset({"Declaration", "Declaration Order"})


def _customs_line_field(row: Any, fieldname: str) -> Any:
    if isinstance(row, dict):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def _sum_customs_line_chargeable_weight(parent_doc: Any) -> float:
    """Sum commercial invoice line chargeable weights (UOM-aware) for customs charge quantity."""
    lines = getattr(parent_doc, "commercial_invoice_line_items", None) or []
    if not lines:
        return 0.0

    company = getattr(parent_doc, "company", None)
    from logistics.utils.measurements import convert_weight, get_default_uoms

    defaults = get_default_uoms(company)
    target_uom = defaults.get("chargeable_weight") or defaults.get("weight")
    total = 0.0

    for row in lines:
        cw = flt(_customs_line_field(row, "chargeable_weight") or 0)
        from_uom = _customs_line_field(row, "chargeable_weight_uom")
        if cw <= 0:
            cw = flt(_customs_line_field(row, "gross_weight") or 0)
            if cw <= 0:
                continue
            from_uom = _customs_line_field(row, "gross_weight_uom")

        if target_uom and from_uom:
            try:
                total += convert_weight(cw, from_uom=from_uom, to_uom=target_uom, company=company)
            except Exception:
                total += cw
        else:
            total += cw

    return flt(total)


@frappe.whitelist()
def sum_customs_line_chargeable_weight(commercial_invoice_line_items=None, company=None):
    """Whitelisted sum of line chargeable weights for desk charge_row_parent_overrides."""
    import json

    if isinstance(commercial_invoice_line_items, str):
        try:
            commercial_invoice_line_items = json.loads(commercial_invoice_line_items)
        except Exception:
            commercial_invoice_line_items = []
    lines = commercial_invoice_line_items or []
    parent = frappe._dict(
        doctype="Declaration",
        company=company,
        commercial_invoice_line_items=[frappe._dict(row) for row in lines],
    )
    return _sum_customs_line_chargeable_weight(parent)


def _get_parent_actual_data(charge_doc: Any, parent_doc: Any) -> Dict:
    """Extract quantity data from parent document for charge calculation.

    On Sales Quote: quantity is estimated (weight, volume, etc. from quote header).
    On Booking/Shipment: quantity is actual (total_weight, chargeable_weight, etc. from packages/actuals).
    """
    if not parent_doc:
        return {
            "actual_quantity": 0,
            "actual_weight": 0,
            "actual_chargeable_weight": 0,
            "actual_volume": 0,
            "actual_distance": 0,
            "actual_pieces": 0,
            "actual_teu": 0,
            "actual_containers": 0,
            "actual_operation_time": 0,
            "actual_item_count": 0,
            "actual_handling_units": 0,
            "actual_trips": 0,
            "actual_days": 0,
            "actual_goods_value": 0,
        }

    parent_doctype = getattr(parent_doc, "doctype", None) or parent_doc.get("doctype")
    fields = PARENT_QUANTITY_FIELDS.get(parent_doctype, ())

    weight = flt(
        _get_field(
            parent_doc,
            "total_weight", "chargeable_weight", "weight", "chargeable",
            "air_weight", "sea_weight", "transport_weight"
        ) or 0
    )
    chargeable_weight = flt(
        _get_field(parent_doc, "chargeable", "chargeable_weight") or 0
    )
    if parent_doctype in _CUSTOMS_PARENT_DOCTYPES:
        line_cw = _sum_customs_line_chargeable_weight(parent_doc)
        if line_cw > 0:
            if chargeable_weight <= 0:
                chargeable_weight = line_cw
            if weight <= 0:
                weight = line_cw
    volume = flt(
        _get_field(
            parent_doc,
            "total_volume", "volume",
            "air_volume", "sea_volume", "transport_volume"
        ) or 0
    )
    if parent_doctype in ("Air Consolidation", "Sea Consolidation") and chargeable_weight <= 0:
        vol_w = volume * (1000.0 / 6.0) if volume else 0.0
        if weight > 0 or vol_w > 0:
            chargeable_weight = max(weight, vol_w)
    pieces = flt(
        _get_field(parent_doc, "total_pieces", "total_packages", "pieces") or 0
    )
    if pieces <= 0 and hasattr(parent_doc, "packages") and parent_doc.packages:
        # Handle both numeric packages (DeclarationOrder) and list/table packages (Sea Booking, Air Booking, etc.)
        if isinstance(parent_doc.packages, (int, float)):
            pieces = flt(parent_doc.packages)
        else:
            pieces = len(parent_doc.packages)
    distance = flt(
        _get_field(
            parent_doc,
            "total_distance", "distance", "transport_distance",
            "distance_km", "total_distance_km"
        ) or 0
    )
    # Sum distance from legs when parent has no total_distance (Transport Order, Transport Job, etc.)
    if distance <= 0:
        distance = _sum_distance_from_legs(parent_doc)
    teu = flt(
        _get_field(parent_doc, "total_teu", "teu") or 0
    )
    containers = flt(_get_field(parent_doc, "total_containers") or 0)
    if containers <= 0 and hasattr(parent_doc, "containers") and parent_doc.containers:
        containers = len(parent_doc.containers)
    if containers <= 0 and hasattr(parent_doc, "consolidation_containers") and parent_doc.consolidation_containers:
        containers = len(parent_doc.consolidation_containers)
    if containers <= 0 and _get_field(parent_doc, "container_no"):
        containers = 1
    operation_time = flt(
        _get_field(parent_doc, "total_operation_time", "operation_time", "actual_hours") or 0
    )

    products = getattr(parent_doc, "project_products", None) or getattr(parent_doc, "products", None) or []
    if isinstance(products, (list, tuple)):
        item_count = len(products)
    else:
        item_count = 0
    if item_count <= 0 and hasattr(parent_doc, "packages") and parent_doc.packages:
        pk = parent_doc.packages
        item_count = len(pk) if isinstance(pk, (list, tuple)) else (cint(pk) if pk else 0)

    handling_units = flt(_get_field(parent_doc, "total_handling_units") or 0)
    if handling_units <= 0 and hasattr(parent_doc, "items") and parent_doc.items:
        hus = set()
        for it in parent_doc.items:
            hu = getattr(it, "handling_unit", None)
            if hu:
                hus.add(hu)
        handling_units = float(len(hus)) if hus else 0.0

    legs = getattr(parent_doc, "legs", None) or getattr(parent_doc, "routing_legs", None) or []
    trip_count = float(len(legs)) if legs else 0.0

    calendar_days = flt(_get_field(parent_doc, "total_days", "calendar_days", "billing_days") or 0)
    goods_value = flt(_get_field(parent_doc, "goods_value", "declared_value") or 0)

    return {
        "actual_quantity": weight or volume or pieces or distance or teu or containers or item_count or handling_units or trip_count or goods_value or 1,
        "actual_weight": weight,
        "actual_chargeable_weight": chargeable_weight,
        "actual_volume": volume,
        "actual_distance": distance,
        "actual_pieces": pieces,
        "actual_teu": teu,
        "actual_containers": containers,
        "actual_operation_time": operation_time,
        "actual_item_count": float(item_count),
        "actual_handling_units": handling_units,
        "actual_trips": trip_count,
        "actual_days": calendar_days if calendar_days > 0 else operation_time,
        "actual_goods_value": goods_value,
    }


def _get_quantity_for_calculation_method(
    actual_data: Dict, method: str, unit_type: str, is_revenue: bool = True
) -> float:
    """Get quantity from parent based on calculation method and unit_type.

    Quantity is the estimated value (Sales Quote) or actual value (Booking/Shipment)
    for the given unit type (weight, volume, pieces, distance, teu, container, etc.).
    """
    if not method:
        return 0.0
    method = (method or "").strip()
    if method in ("Flat Rate", "Fixed Amount"):
        return 1.0
    if method == "Percentage":
        return 1.0
    if method == "Weight Break":
        return flt(actual_data.get("actual_weight") or 0)
    if method == "Qty Break":
        return flt(
            actual_data.get("actual_pieces") or actual_data.get("actual_weight") or 1
        )
    if method == "Percentage Break":
        # Tier comparison uses quantity; goods value is resolved separately for the amount.
        return flt(actual_data.get("actual_quantity") or 0)
    # Per Unit, Base Plus Additional, First Plus Additional, Location-based
    ut = (unit_type or "Weight").strip().lower()
    if ut == "weight":
        return flt(actual_data.get("actual_weight") or 0)
    if ut == "chargeable weight":
        cw = flt(actual_data.get("actual_chargeable_weight") or 0)
        if cw > 0:
            return cw
        return flt(actual_data.get("actual_weight") or 0)
    if ut == "volume":
        return flt(actual_data.get("actual_volume") or 0)
    if ut in ("piece", "package"):
        return flt(actual_data.get("actual_pieces") or 0)
    if ut == "distance":
        return flt(actual_data.get("actual_distance") or 0)
    if ut == "teu":
        return flt(actual_data.get("actual_teu") or 0)
    if ut == "container":
        return flt(actual_data.get("actual_containers") or 0)
    if ut == "operation time":
        return flt(actual_data.get("actual_operation_time") or 1)
    if ut == "day":
        d = flt(actual_data.get("actual_days") or 0)
        if d > 0:
            return d
        return flt(actual_data.get("actual_operation_time") or 1)
    if ut == "item count":
        return flt(actual_data.get("actual_item_count") or 0)
    if ut == "handling unit":
        hu = flt(actual_data.get("actual_handling_units") or 0)
        return hu if hu > 0 else 1.0
    if ut == "job":
        # Per-job flat unit: always 1 for the operational parent (do not use
        # actual_quantity — that falls back to weight/volume and inflates Job qty).
        return 1.0
    if ut == "trip":
        t = flt(actual_data.get("actual_trips") or 0)
        return t if t > 0 else 1.0
    if ut == "shipment":
        return 1.0
    if ut == "value":
        gv = flt(actual_data.get("actual_goods_value") or 0)
        if gv > 0:
            return gv
        return flt(actual_data.get("actual_quantity") or 0)
    return flt(actual_data.get("actual_quantity") or 0)


def _spread_row_qty_into_actual_data(actual_data: Dict, unit_type: str, qty_val: float) -> None:
    """Map charge-row quantity into parent actual aggregates for the given unit_type."""
    actual_data["actual_quantity"] = qty_val
    ut = (unit_type or "Weight").strip().lower()
    if ut == "weight":
        actual_data["actual_weight"] = qty_val
    elif ut == "chargeable weight":
        actual_data["actual_chargeable_weight"] = qty_val
    elif ut == "volume":
        actual_data["actual_volume"] = qty_val
    elif ut in ("piece", "package"):
        actual_data["actual_pieces"] = qty_val
    elif ut == "distance":
        actual_data["actual_distance"] = qty_val
    elif ut == "teu":
        actual_data["actual_teu"] = qty_val
    elif ut == "container":
        actual_data["actual_containers"] = qty_val
    elif ut == "operation time":
        actual_data["actual_operation_time"] = qty_val
    elif ut == "day":
        actual_data["actual_days"] = qty_val
        actual_data["actual_operation_time"] = qty_val
    elif ut == "item count":
        actual_data["actual_item_count"] = qty_val
    elif ut == "handling unit":
        actual_data["actual_handling_units"] = qty_val
    elif ut == "trip":
        actual_data["actual_trips"] = qty_val
    elif ut == "job":
        actual_data["actual_quantity"] = qty_val
    elif ut == "value":
        actual_data["actual_goods_value"] = qty_val


def get_quantity_from_parent_by_unit_type(parent_doc: Any, unit_type: Optional[str]) -> float:
    """Resolve quantity from an operational parent (Air Booking, Air Shipment, …) by ``unit_type``.

    Uses the same aggregates as ``calculate_charge_row`` so Sales Quote → Booking/Shipment
    charge mapping stays aligned with grid calculations.
    """
    if not parent_doc:
        return 1.0
    ut = (unit_type or "").strip()
    if not ut:
        return 1.0
    actual_data = _get_parent_actual_data(None, parent_doc)
    return _get_quantity_for_calculation_method(actual_data, "Per Unit", ut, is_revenue=True)


def realign_charge_row_quantities_from_parent(
    charge_doc: Any, parent_doc: Optional[Any]
) -> None:
    """Set Per Unit quantity/cost_quantity from parent metrics and unit_type (Job → 1, not weight)."""
    if not parent_doc:
        return
    rev_method = _get_field(charge_doc, *REVENUE_METHOD_FIELDS)
    if rev_method == "Per Unit":
        ut = _get_field(charge_doc, *UNIT_TYPE_FIELDS)
        if ut and hasattr(charge_doc, "quantity"):
            charge_doc.quantity = get_quantity_from_parent_by_unit_type(parent_doc, ut)
    cost_method = _get_field(charge_doc, *COST_METHOD_FIELDS)
    if cost_method == "Per Unit":
        cut = _get_field(charge_doc, *COST_UNIT_TYPE_FIELDS)
        if cut and hasattr(charge_doc, "cost_quantity"):
            charge_doc.cost_quantity = get_quantity_from_parent_by_unit_type(parent_doc, cut)


def _normalize_calculation_method(method: str, unit_type: str) -> tuple:
    """Map legacy values (e.g. Per kg) to engine calculation_method and unit_type."""
    if not method:
        return None, unit_type or "Weight"
    mapped = METHOD_TO_ENGINE.get(method.strip())
    if mapped:
        calc_method, mapped_unit = mapped
        return calc_method, mapped_unit or unit_type or "Weight"
    return method, unit_type or "Weight"


def _get_item_code_from_charge(charge_doc: Any) -> Optional[str]:
    """Get item code from charge doc (supports item_code or charge_item)."""
    return _get_field(charge_doc, "item_code", "charge_item")


def _main_job_charge_cost_for_item(main_doc: Any, item_code: Optional[str]) -> float:
    """Sum actual/estimated cost on main job charge rows matching item_code (internal job revenue source)."""
    if not item_code:
        return 0.0
    total = 0.0
    for ch in main_doc.get("charges") or []:
        row_item = _get_item_code_from_charge(ch)
        if row_item != item_code:
            continue
        c = flt(getattr(ch, "actual_cost", 0)) or flt(getattr(ch, "estimated_cost", 0))
        if c > 0:
            total += c
    return total


def _item_fallback_buying_or_standard_rate(item_code: Optional[str]) -> float:
    """Default cost rate: Item.standard_rate, else latest buying Item Price."""
    if not item_code:
        return 0.0
    std = frappe.db.get_value("Item", item_code, "standard_rate")
    if flt(std) > 0:
        return flt(std)
    row = frappe.db.sql(
        """SELECT price_list_rate FROM `tabItem Price`
			WHERE item_code=%s AND IFNULL(buying, 0)=1 ORDER BY modified DESC LIMIT 1""",
        (item_code,),
    )
    if row and row[0][0] is not None:
        return flt(row[0][0])
    return 0.0


def _resolve_parent_doc_for_charge(charge_doc: Any, parent_doc: Optional[Any]) -> Optional[Any]:
    if parent_doc is not None:
        return parent_doc
    parent_name = getattr(charge_doc, "parent", None)
    parenttype = getattr(charge_doc, "parenttype", None)
    if not parent_name or not parenttype or str(parent_name).startswith("new-") or parent_name in ("new", ""):
        return None
    cache = getattr(frappe.local, _CHARGE_RESOLUTION_PARENT_KEY, None) or {}
    cached = cache.get((parenttype, parent_name))
    if cached is not None:
        return cached
    try:
        return frappe.get_doc(parenttype, parent_name)
    except Exception:
        return None


def _resolve_quantity_context_parent(charge_doc: Any, parent_doc: Optional[Any]) -> Optional[Any]:
    """Use linked job weights/volumes when charge rows sit on Change Request."""
    if (
        parent_doc
        and getattr(parent_doc, "doctype", None) == "Change Request"
        and getattr(charge_doc, "parenttype", None) == "Change Request"
    ):
        jt = getattr(parent_doc, "job_type", None)
        jn = getattr(parent_doc, "job", None)
        if jt and jn and frappe.db.exists(jt, jn):
            try:
                return frappe.get_doc(jt, jn)
            except Exception:
                pass
    return parent_doc


INTERNAL_JOB_MAIN_JOB_TYPES = (
    "Air Shipment",
    "Sea Shipment",
    "Transport Job",
    "Declaration",
)


def _first_nonempty(*values):
    """Return the first value that is not None or empty string (0 is kept)."""
    for val in values:
        if val is None or val == "":
            continue
        return val
    return None


def _tariff_rate_row_to_rate_data(rate, is_revenue: bool = True) -> Optional[Dict]:
    """Build uniform rate_data for _fetch_rates_from_tariff from a Tariff Charge row.

    When is_revenue is False, prefer dual-side cost fields (unit_cost, cost_*), falling
    back to revenue/legacy keys so MICE-style tariffs that only fill unit_rate still work.
    """
    as_dict = getattr(rate, "as_dict", None)
    d = as_dict() if callable(as_dict) else dict(rate)
    if is_revenue:
        raw = _first_nonempty(d.get("rate"), d.get("rate_value"), d.get("unit_rate"))
        method = (
            (d.get("calculation_method") or d.get("revenue_calculation_method") or "Per Unit") or ""
        ).strip()
        return {
            "calculation_method": method,
            "rate": flt(raw or 0),
            "unit_type": d.get("unit_type") or "Weight",
            "currency": d.get("currency") or "USD",
            "minimum_quantity": flt(d.get("minimum_quantity", 0) or 0),
            "minimum_charge": flt(d.get("minimum_charge", 0) or 0),
            "maximum_charge": flt(d.get("maximum_charge", 0) or 0),
            "base_amount": flt(d.get("base_amount", 0) or 0),
            "uom": d.get("uom"),
            "quantity": flt(d.get("quantity") or 0),
        }

    raw = _first_nonempty(
        d.get("unit_cost"),
        d.get("rate"),
        d.get("rate_value"),
        d.get("unit_rate"),
    )
    method = (
        (d.get("cost_calculation_method") or d.get("calculation_method") or "Per Unit") or ""
    ).strip()
    return {
        "calculation_method": method,
        "rate": flt(raw or 0),
        "unit_type": d.get("cost_unit_type") or d.get("unit_type") or "Weight",
        "currency": d.get("cost_currency") or d.get("currency") or "USD",
        "minimum_quantity": flt(
            _first_nonempty(d.get("cost_minimum_quantity"), d.get("minimum_quantity"), 0) or 0
        ),
        "minimum_charge": flt(
            _first_nonempty(d.get("cost_minimum_charge"), d.get("minimum_charge"), 0) or 0
        ),
        "maximum_charge": flt(
            _first_nonempty(d.get("cost_maximum_charge"), d.get("maximum_charge"), 0) or 0
        ),
        "base_amount": flt(
            _first_nonempty(d.get("cost_base_amount"), d.get("base_amount"), 0) or 0
        ),
        "uom": d.get("cost_uom") or d.get("uom"),
        "quantity": flt(d.get("cost_quantity") or 0),
    }


def _find_tariff_rate_match(
    tariff_name: str,
    item_code: str,
    service_type: Optional[str] = None,
    is_revenue: bool = True,
) -> Optional[Tuple[Dict, Any, str]]:
    """
    Find matching Tariff Charge row by item_code and optional service type.
    Returns (normalized rate_data dict, raw child row, parentfield name).
    Pass is_revenue=False to normalize cost-side pricing fields.
    """
    if not tariff_name or not item_code:
        return None
    try:
        tariff_doc = frappe.get_doc("Tariff", tariff_name)
    except Exception:
        return None

    want = canonical_charge_service_type_for_storage((service_type or "").strip())
    rows: List[Any] = list(getattr(tariff_doc, "rates", None) or [])
    if want:
        matching = [r for r in rows if canonical_charge_service_type_for_storage(getattr(r, "service_type", "") or "") == want]
        rest = [r for r in rows if r not in matching]
        rows = matching + rest
    for rate in rows:
        if getattr(rate, "item_code", None) != item_code:
            continue
        if want and canonical_charge_service_type_for_storage(getattr(rate, "service_type", "") or "") != want:
            continue
        return (_tariff_rate_row_to_rate_data(rate, is_revenue=is_revenue), rate, "rates")
    return None


# Meta + pricing fields applied via _apply_tariff_rate_data_to_charge (not copied from raw row)
TARIFF_CONTEXT_COPY_SKIP = frozenset(
    {
        "name",
        "idx",
        "owner",
        "creation",
        "modified",
        "modified_by",
        "docstatus",
        "parent",
        "parentfield",
        "parenttype",
        "doctype",
        "item_code",
        "item",
        "item_name",
        "description",
        "is_active",
        "valid_from",
        "valid_to",
        "calculation_method",
        "rate",
        "rate_value",
        "currency",
        "minimum_charge",
        "maximum_charge",
        "minimum_quantity",
        "base_amount",
        "uom",
        "unit_type",
        "revenue_calculation_method",
        "cost_calculation_method",
        "unit_rate",
        "unit_cost",
        "cost_uom",
        "cost_unit_type",
        "cost_currency",
        "cost_minimum_quantity",
        "cost_minimum_charge",
        "cost_maximum_charge",
        "cost_base_amount",
        "quantity",
        "cost_quantity",
        "tariff_valid_from",
        "tariff_valid_to",
        "tariff_rate_active",
        "estimated_revenue",
        "estimated_cost",
        "charge_type",
        "quotation_type",
        "charge_group",
        "cost_sheet_source",
        "revenue_calc_notes",
        "cost_calc_notes",
    }
)

# Air tariff uses UNLOCO airport fields; Sales Quote Charge uses origin/destination_port
TARIFF_TO_CHARGE_FIELD_ALIASES = {
    "origin_airport": "origin_port",
    "destination_airport": "destination_port",
}


def _copy_tariff_line_context_to_charge(charge_doc: Any, rate_row: Any) -> None:
    """Copy route, equipment, and other line fields from a Tariff child row onto the charge when the field exists."""
    if not rate_row:
        return
    d = rate_row.as_dict() if hasattr(rate_row, "as_dict") else dict(rate_row)
    child_dt = d.get("doctype") or ""
    for key, val in d.items():
        if key in TARIFF_CONTEXT_COPY_SKIP or val is None or val == "":
            continue
        if key == "service_type" and child_dt == "Sea Freight Rate":
            continue
        target = TARIFF_TO_CHARGE_FIELD_ALIASES.get(key, key)
        if not hasattr(charge_doc, target):
            continue
        try:
            setattr(charge_doc, target, val)
        except Exception:
            pass


def _fill_item_name_on_charge_from_item(charge_doc: Any) -> None:
    ic = _get_item_code_from_charge(charge_doc)
    if not ic or not hasattr(charge_doc, "item_name"):
        return
    iname = frappe.db.get_value("Item", ic, "item_name")
    if iname:
        charge_doc.item_name = iname


# Fields to send back to desk so tariff rate + context populate the child row in the grid
CHARGE_ROW_CLIENT_EXPORT_FIELDS = (
    "revenue_calculation_method",
    "calculation_method",
    "unit_rate",
    "unit_type",
    "currency",
    "quantity",
    "uom",
    "minimum_quantity",
    "minimum_charge",
    "maximum_charge",
    "base_amount",
    "item_name",
    "cost_calculation_method",
    "unit_cost",
    "cost_unit_type",
    "cost_currency",
    "cost_quantity",
    "cost_uom",
    "cost_minimum_quantity",
    "cost_minimum_charge",
    "cost_maximum_charge",
    "cost_base_amount",
    "use_tariff_in_revenue",
    "use_tariff_in_cost",
    "use_unit_breaks",
    "cost_use_unit_breaks",
    "load_type",
    "vehicle_type",
    "container_type",
    "location_type",
    "location_from",
    "location_to",
    "origin_port",
    "destination_port",
    "shipping_line",
    "airline",
    "air_house_type",
    "sea_house_type",
    "freight_agent",
    "freight_agent_sea",
    "transport_mode",
    "direction",
    "customs_authority",
    "declaration_type",
    "customs_broker",
    "customs_charge_category",
    "pick_mode",
    "drop_mode",
    "transport_template",
)


def _charge_row_sync_dict_for_client(charge_doc: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for f in CHARGE_ROW_CLIENT_EXPORT_FIELDS:
        if hasattr(charge_doc, f):
            out[f] = getattr(charge_doc, f)
    return out


def _apply_tariff_rate_data_revenue(charge_doc: Any, rate_data: Dict) -> None:
    method = rate_data.get("calculation_method") or "Per Unit"
    if hasattr(charge_doc, "revenue_calculation_method"):
        charge_doc.revenue_calculation_method = method
    if hasattr(charge_doc, "calculation_method"):
        charge_doc.calculation_method = method
    rate_val = rate_data.get("rate", 0)
    if hasattr(charge_doc, "unit_rate"):
        charge_doc.unit_rate = rate_val
    if hasattr(charge_doc, "unit_type"):
        charge_doc.unit_type = rate_data.get("unit_type")
    if hasattr(charge_doc, "currency"):
        charge_doc.currency = rate_data.get("currency") or "USD"
    if hasattr(charge_doc, "minimum_quantity"):
        charge_doc.minimum_quantity = rate_data.get("minimum_quantity", 0)
    if hasattr(charge_doc, "minimum_charge"):
        charge_doc.minimum_charge = rate_data.get("minimum_charge", 0)
    if hasattr(charge_doc, "maximum_charge"):
        charge_doc.maximum_charge = rate_data.get("maximum_charge", 0)
    if hasattr(charge_doc, "base_amount"):
        charge_doc.base_amount = rate_data.get("base_amount", 0)
    if hasattr(charge_doc, "uom"):
        charge_doc.uom = rate_data.get("uom")
    if hasattr(charge_doc, "quantity") and "quantity" in rate_data:
        charge_doc.quantity = rate_data.get("quantity", 0)


def _charge_doc_has_field(charge_doc: Any, fieldname: str) -> bool:
    """True when field exists on the charge doctype meta (or key on plain/_dict test objects)."""
    meta = getattr(charge_doc, "meta", None)
    if meta is not None and getattr(meta, "has_field", None):
        return bool(meta.has_field(fieldname))
    if isinstance(charge_doc, dict):
        return fieldname in charge_doc
    try:
        from frappe import _dict as _frappe_dict
    except Exception:
        _frappe_dict = None
    if _frappe_dict is not None and isinstance(charge_doc, _frappe_dict):
        return fieldname in charge_doc
    return fieldname in getattr(charge_doc, "__dict__", {})


_CONSOLIDATION_STYLE_CALC_METHODS = frozenset(
	{
		"Per Unit",
		"Fixed Amount",
		"Flat Rate",
		"Base Plus Additional",
		"First Plus Additional",
		"Percentage",
		"Location-based",
		"Weight Break",
		"Qty Break",
		"Percentage Break",
	}
)


def _apply_tariff_rate_data_cost(charge_doc: Any, rate_data: Dict) -> None:
    method = rate_data.get("calculation_method") or "Per Unit"
    # Dual-side charge tables (unit_cost / cost_*) — prefer those when present.
    if _charge_doc_has_field(charge_doc, "unit_cost") or _charge_doc_has_field(
        charge_doc, "cost_calculation_method"
    ):
        if hasattr(charge_doc, "cost_calculation_method"):
            charge_doc.cost_calculation_method = method
        if hasattr(charge_doc, "unit_cost"):
            charge_doc.unit_cost = rate_data.get("rate", 0)
        if hasattr(charge_doc, "cost_unit_type"):
            charge_doc.cost_unit_type = rate_data.get("unit_type")
        if hasattr(charge_doc, "cost_currency"):
            charge_doc.cost_currency = rate_data.get("currency") or "USD"
        if hasattr(charge_doc, "cost_minimum_quantity"):
            charge_doc.cost_minimum_quantity = rate_data.get("minimum_quantity", 0)
        if hasattr(charge_doc, "cost_minimum_charge"):
            charge_doc.cost_minimum_charge = rate_data.get("minimum_charge", 0)
        if hasattr(charge_doc, "cost_maximum_charge"):
            charge_doc.cost_maximum_charge = rate_data.get("maximum_charge", 0)
        if hasattr(charge_doc, "cost_base_amount"):
            charge_doc.cost_base_amount = rate_data.get("base_amount", 0)
        if hasattr(charge_doc, "cost_uom"):
            charge_doc.cost_uom = rate_data.get("uom")
        if hasattr(charge_doc, "cost_quantity") and "quantity" in rate_data:
            charge_doc.cost_quantity = rate_data.get("quantity", 0)
        return

    # Single-side cost tables (e.g. MICE Project Consolidation Charges): map onto unit_rate.
    if not _charge_doc_has_field(charge_doc, "unit_rate"):
        return
    if (
        _charge_doc_has_field(charge_doc, "revenue_calculation_method")
        and method in _CONSOLIDATION_STYLE_CALC_METHODS
    ):
        charge_doc.revenue_calculation_method = method
    charge_doc.unit_rate = rate_data.get("rate", 0)
    unit_type = rate_data.get("unit_type")
    if unit_type and _charge_doc_has_field(charge_doc, "unit_type"):
        df = charge_doc.meta.get_field("unit_type") if getattr(charge_doc, "meta", None) else None
        options = (getattr(df, "options", None) or "").split("\n") if df else []
        if not options or unit_type in options:
            charge_doc.unit_type = unit_type
    if _charge_doc_has_field(charge_doc, "currency"):
        charge_doc.currency = rate_data.get("currency") or "USD"
    uom = rate_data.get("uom")
    if uom and _charge_doc_has_field(charge_doc, "unit_of_measure"):
        df = charge_doc.meta.get_field("unit_of_measure") if getattr(charge_doc, "meta", None) else None
        # Select fields gate on option membership; Link→UOM always accepts tariff UOM.
        if df and getattr(df, "fieldtype", None) == "Select":
            options = (getattr(df, "options", None) or "").split("\n")
            if options and uom not in options:
                uom = None
        if uom:
            charge_doc.unit_of_measure = uom
    elif uom and _charge_doc_has_field(charge_doc, "uom"):
        charge_doc.uom = uom


def _charge_reference_is_persistable(charge_doc: Any) -> bool:
    """True when charge row has a saved name that Dynamic Link break rows can reference.

    Mid-insert child rows get hash names (not ``new-*``) before ``db_insert``; those must
    not be treated as persistable or Charge Unit Break Dynamic Links fail validation.
    """
    name = getattr(charge_doc, "name", None)
    doctype = getattr(charge_doc, "doctype", None)
    if not name or not doctype or str(name).startswith("new"):
        return False
    return bool(frappe.db.exists(doctype, name))


def sync_tariff_rates_and_breaks_on_charges(parent_doc: Any) -> None:
    """Fetch tariff rates/Unit Breaks onto charge rows after children are in the DB.

    Parent validate often runs charge calc before child ``db_insert``, so Unit Break
    Dynamic Links cannot resolve yet. Call this from ``after_insert`` / ``on_update``.
    """
    for ch in parent_doc.get("charges") or []:
        if not (
            getattr(ch, "revenue_tariff", None)
            or getattr(ch, "cost_tariff", None)
            or getattr(ch, "tariff", None)
        ):
            continue
        try:
            ch._logistics_tariff_fetch_applied = False
        except Exception:
            pass
        _fetch_rates_from_tariff_if_needed(ch)


def _tariff_rate_has_unit_breaks(tariff_rate_name: str, record_type: str) -> bool:
    if not tariff_rate_name or not frappe.db.exists("DocType", "Charge Unit Break"):
        return False
    return bool(
        frappe.db.exists(
            "Charge Unit Break",
            {
                "reference_doctype": "Tariff Charge",
                "reference_no": tariff_rate_name,
                "type": record_type,
            },
        )
    )


def _copy_tariff_unit_breaks_to_charge(
    charge_doc: Any, rate_row: Any, record_type: str
) -> None:
    """Copy Unit Break tiers from a Tariff Charge line onto the charge; enable the checkbox.

    Unsaved / mid-insert charge names only get the checkbox — tiers need a DB-backed reference_no.
    """
    rate_name = getattr(rate_row, "name", None) if rate_row else None
    if not rate_name:
        return
    if not _tariff_rate_has_unit_breaks(rate_name, record_type):
        return

    flag_field = "use_unit_breaks" if record_type == "Selling" else "cost_use_unit_breaks"
    if hasattr(charge_doc, flag_field):
        setattr(charge_doc, flag_field, 1)

    if not _charge_reference_is_persistable(charge_doc):
        return

    to_dt = getattr(charge_doc, "doctype", None) or ""
    to_no = getattr(charge_doc, "name", None)
    if not to_dt or not to_no:
        return

    # Persist checkbox — after_insert/on_update mutations are not re-saved to the child row.
    try:
        frappe.db.set_value(to_dt, to_no, flag_field, 1, update_modified=False)
    except Exception:
        pass

    from logistics.utils.sales_quote_programme_charges import copy_charge_breaks_for_reference

    copy_charge_breaks_for_reference(
        "Tariff Charge",
        rate_name,
        to_dt,
        to_no,
        record_types=(record_type,),
    )


def _fetch_rates_from_tariff_if_needed(charge_doc: Any) -> None:
    """
    When item_code and revenue_tariff and/or cost_tariff are set, load the matching line from the
    Tariff doctype: fill revenue/cost rate fields, route & equipment from the line where applicable,
    copy Unit Breaks when present, and turn on the corresponding Use Tariff checkboxes.
    (use_tariff_in_* is not required to fetch.)
    """
    if getattr(charge_doc, "_logistics_tariff_fetch_applied", False):
        return
    item_code = _get_item_code_from_charge(charge_doc)
    if not item_code:
        return

    st = getattr(charge_doc, "service_type", None)
    saved_currency = getattr(charge_doc, "currency", None) or None
    saved_cost_currency = getattr(charge_doc, "cost_currency", None) or None
    using_rev_tariff = cint(getattr(charge_doc, "use_tariff_in_revenue", 0))
    using_cost_tariff = cint(getattr(charge_doc, "use_tariff_in_cost", 0))

    # Revenue: revenue_tariff (legacy: generic tariff) + item
    rev_tariff = getattr(charge_doc, "revenue_tariff", None) or getattr(charge_doc, "tariff", None)
    if rev_tariff:
        match = _find_tariff_rate_match(rev_tariff, item_code, st, is_revenue=True)
        if match:
            rate_data, rate_row, _tname = match
            _apply_tariff_rate_data_revenue(charge_doc, rate_data)
            _copy_tariff_line_context_to_charge(charge_doc, rate_row)
            _copy_tariff_unit_breaks_to_charge(charge_doc, rate_row, "Selling")
            if hasattr(charge_doc, "use_tariff_in_revenue"):
                charge_doc.use_tariff_in_revenue = 1
            # Keep user-entered revenue currency unless they opted into tariff rates
            if not using_rev_tariff and saved_currency:
                charge_doc.currency = saved_currency

    # Cost: cost_tariff (legacy: generic tariff) + item
    cost_tariff = getattr(charge_doc, "cost_tariff", None) or getattr(charge_doc, "tariff", None)
    if cost_tariff:
        match = _find_tariff_rate_match(cost_tariff, item_code, st, is_revenue=False)
        if match:
            rate_data, rate_row, _tname = match
            _apply_tariff_rate_data_cost(charge_doc, rate_data)
            _copy_tariff_line_context_to_charge(charge_doc, rate_row)
            _copy_tariff_unit_breaks_to_charge(charge_doc, rate_row, "Cost")
            if hasattr(charge_doc, "use_tariff_in_cost"):
                charge_doc.use_tariff_in_cost = 1
            # Keep user-entered cost currency unless they opted into tariff rates
            if not using_cost_tariff and saved_cost_currency:
                charge_doc.cost_currency = saved_cost_currency

    _fill_item_name_on_charge_from_item(charge_doc)
    try:
        charge_doc._logistics_tariff_fetch_applied = True
    except Exception:
        pass


def _has_billable_rate_input(charge_doc: Any, is_revenue: bool = True) -> bool:
    """True when the user has entered enough pricing input to show an estimated amount."""
    if is_revenue:
        method = (_get_field(charge_doc, *REVENUE_METHOD_FIELDS) or "").strip()
        rate = flt(_get_field(charge_doc, *RATE_FIELDS) or 0)
        prefix = ""
    else:
        method = (_get_field(charge_doc, *COST_METHOD_FIELDS) or "").strip()
        rate = flt(_get_field(charge_doc, *COST_RATE_FIELDS) or 0)
        prefix = "cost_"

    if not method:
        return False
    if method in ("Weight Break", "Qty Break", "Percentage Break"):
        return True
    if method == "Percentage":
        base = flt(getattr(charge_doc, f"{prefix}base_amount", None) or 0)
        return rate > 0 and base > 0
    return rate > 0


def _estimated_display_amount(charge_doc: Any, amount: Any, is_revenue: bool = True):
    """Return None so Currency fields stay empty until pricing input exists; otherwise the amount."""
    if not _has_billable_rate_input(charge_doc, is_revenue):
        return None
    return flt(amount)


def _prepare_rate_data(
    charge_doc: Any,
    is_revenue: bool = True,
) -> Optional[Dict]:
    """Prepare rate data dict for RateCalculationEngine from charge doc."""
    if is_revenue:
        method = _get_field(charge_doc, *REVENUE_METHOD_FIELDS)
        rate = flt(_get_field(charge_doc, *RATE_FIELDS) or 0)
        unit_type = _get_field(charge_doc, *UNIT_TYPE_FIELDS) or "Weight"
        prefix = ""
    else:
        method = _get_field(charge_doc, *COST_METHOD_FIELDS)
        rate = flt(_get_field(charge_doc, *COST_RATE_FIELDS) or 0)
        unit_type = _get_field(charge_doc, *COST_UNIT_TYPE_FIELDS) or "Weight"
        prefix = "cost_"

    if not method:
        return None

    # Map legacy method values to engine format
    method, unit_type = _normalize_calculation_method(method, unit_type)

    # Weight Break, Qty Break, and Percentage Break are handled separately
    if method in ("Weight Break", "Qty Break", "Percentage Break"):
        return None

    uom = getattr(charge_doc, "uom", None) or getattr(charge_doc, f"{prefix}uom", None)
    if is_revenue:
        currency = getattr(charge_doc, "currency", None) or "USD"
    else:
        currency = getattr(charge_doc, "cost_currency", None) or getattr(charge_doc, "currency", None) or "USD"
    rate_data = {
        "calculation_method": method,
        "rate": rate,
        "unit_type": unit_type or "Weight",
        "uom": (uom or "").strip() or None,
        "minimum_quantity": flt(getattr(charge_doc, f"{prefix}minimum_quantity", None) or 0),
        "minimum_unit_rate": flt(getattr(charge_doc, f"{prefix}minimum_unit_rate", None) or 0),
        "minimum_charge": flt(getattr(charge_doc, f"{prefix}minimum_charge", None) or 0),
        "maximum_charge": flt(getattr(charge_doc, f"{prefix}maximum_charge", None) or 0),
        "base_amount": flt(getattr(charge_doc, f"{prefix}base_amount", None) or 0),
        "base_quantity": flt(getattr(charge_doc, f"{prefix}base_quantity", None) or 1),
        "currency": currency,
        "item_code": getattr(charge_doc, "item_code", None),
        "item_name": getattr(charge_doc, "item_name", None),
    }
    return rate_data


def _resolve_weight_break_rate(
    charge_doc: Any,
    actual_weight: float,
    record_type: str = "Selling",
) -> Optional[Dict]:
    """Resolve applicable unit rate from Sales Quote Weight Break (reference-based, same as Sales Quote)."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None

    weight_breaks = frappe.get_all(
        "Sales Quote Weight Break",
        filters={
            "reference_doctype": charge_doc.doctype,
            "reference_no": ref_name,
            "type": record_type,
        },
        fields=["weight_break", "unit_rate", "rate_type", "currency"],
        order_by="weight_break asc",
    )
    if not weight_breaks:
        return None

    sorted_breaks = sorted(
        weight_breaks,
        key=lambda x: flt(x.get("weight_break", 0)),
        reverse=True,
    )
    for wb in sorted_breaks:
        if flt(actual_weight) >= flt(wb.get("weight_break", 0)):
            return wb
    return sorted(weight_breaks, key=lambda x: flt(x.get("weight_break", 0)))[0]


def _resolve_qty_break_rate(
    charge_doc: Any,
    actual_qty: float,
    record_type: str = "Selling",
) -> Optional[Dict]:
    """Resolve applicable unit rate from Sales Quote Qty Break (reference-based, same as Sales Quote)."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None

    qty_breaks = frappe.get_all(
        "Sales Quote Qty Break",
        filters={
            "reference_doctype": charge_doc.doctype,
            "reference_no": ref_name,
            "type": record_type,
        },
        fields=["qty_break", "unit_rate", "currency"],
        order_by="qty_break asc",
    )
    if not qty_breaks:
        return None

    sorted_breaks = sorted(
        qty_breaks,
        key=lambda x: flt(x.get("qty_break", 0)),
        reverse=True,
    )
    for qb in sorted_breaks:
        if flt(actual_qty) >= flt(qb.get("qty_break", 0)):
            return qb
    return sorted(qty_breaks, key=lambda x: flt(x.get("qty_break", 0)))[0]


def _resolve_percentage_break_rate(
    charge_doc: Any,
    comparison_qty: float,
    record_type: str = "Selling",
) -> Optional[Dict]:
    """Resolve applicable percentage from Sales Quote Percentage Break by Quantity tier."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None

    percentage_breaks = frappe.get_all(
        "Sales Quote Percentage Break",
        filters={
            "reference_doctype": charge_doc.doctype,
            "reference_no": ref_name,
            "type": record_type,
        },
        fields=["value_break", "percentage_rate", "rate_type", "currency"],
        order_by="value_break asc",
    )
    if not percentage_breaks:
        return None

    sorted_breaks = sorted(
        percentage_breaks,
        key=lambda x: flt(x.get("value_break", 0)),
        reverse=True,
    )
    for pb in sorted_breaks:
        if flt(comparison_qty) >= flt(pb.get("value_break", 0)):
            return pb
    return sorted(percentage_breaks, key=lambda x: flt(x.get("value_break", 0)))[0]


def _charge_side_uses_unit_breaks(charge_doc: Any, is_revenue: bool) -> bool:
    if is_revenue:
        return cint(getattr(charge_doc, "use_unit_breaks", 0))
    return cint(getattr(charge_doc, "cost_use_unit_breaks", 0))


def _resolve_unit_break_rate(
    charge_doc: Any,
    comparison_qty: float,
    record_type: str = "Selling",
    unit_type: Optional[str] = None,
) -> Optional[Dict]:
    """Resolve applicable unit rate from Charge Unit Break tiers."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None
    if not frappe.db.exists("DocType", "Charge Unit Break"):
        return None

    filters = {
        "reference_doctype": charge_doc.doctype,
        "reference_no": ref_name,
        "type": record_type,
    }
    if unit_type:
        filters["unit_type"] = unit_type

    unit_breaks = frappe.get_all(
        "Charge Unit Break",
        filters=filters,
        fields=["unit_type", "unit_break", "unit_rate", "currency"],
        order_by="unit_break asc",
    )
    if not unit_breaks and unit_type:
        unit_breaks = frappe.get_all(
            "Charge Unit Break",
            filters={
                "reference_doctype": charge_doc.doctype,
                "reference_no": ref_name,
                "type": record_type,
            },
            fields=["unit_type", "unit_break", "unit_rate", "currency"],
            order_by="unit_break asc",
        )
    if not unit_breaks:
        return None

    sorted_breaks = sorted(
        unit_breaks,
        key=lambda x: flt(x.get("unit_break", 0)),
        reverse=True,
    )
    for row in sorted_breaks:
        if flt(comparison_qty) >= flt(row.get("unit_break", 0)):
            return row
    return sorted(unit_breaks, key=lambda x: flt(x.get("unit_break", 0)))[0]


def _unit_break_uom_label(unit_type: str, charge_doc: Any, is_revenue: bool) -> str:
    ut = (unit_type or "Weight").strip()
    engine = RateCalculationEngine()
    uom = engine.unit_types.get(ut)
    if uom:
        return uom
    if ut.lower() == "value":
        if is_revenue:
            return getattr(charge_doc, "currency", None) or "USD"
        return (
            getattr(charge_doc, "cost_currency", None)
            or getattr(charge_doc, "currency", None)
            or "USD"
        )
    prefix = "" if is_revenue else "cost_"
    return getattr(charge_doc, f"{prefix}uom", None) or getattr(charge_doc, "uom", None) or ut


def _sync_break_tier_rate_to_charge_row(
    charge_doc: Any, rate: float, is_revenue: bool
) -> None:
    """Copy matched Weight/Qty/Percentage Break tier rate onto the charge row for display."""
    if is_revenue and hasattr(charge_doc, "unit_rate"):
        charge_doc.unit_rate = rate
    elif not is_revenue and hasattr(charge_doc, "unit_cost"):
        charge_doc.unit_cost = rate


def _apply_unit_break_to_rate_data(
    charge_doc: Any,
    rate_data: Dict,
    actual_data: Dict,
    unit_type: str,
    record_type: str,
    is_revenue: bool,
) -> Optional[str]:
    """When Unit Breaks is enabled, resolve tier rate and override rate_data. Returns detail prefix or None."""
    if not _charge_side_uses_unit_breaks(charge_doc, is_revenue):
        return None

    comparison_qty = _get_quantity_for_calculation_method(
        actual_data, "Per Unit", unit_type, is_revenue=is_revenue
    )
    applicable = _resolve_unit_break_rate(
        charge_doc, comparison_qty, record_type, unit_type=unit_type
    )
    if not applicable:
        return None

    tier_rate = flt(applicable.get("unit_rate", 0))
    original_rate = flt(rate_data.get("rate", 0))
    rate_data["rate"] = tier_rate
    rate_data["unit_rate"] = tier_rate
    if is_revenue and hasattr(charge_doc, "unit_rate"):
        charge_doc.unit_rate = tier_rate
    elif not is_revenue and hasattr(charge_doc, "unit_cost"):
        charge_doc.unit_cost = tier_rate

    ut_label = (unit_type or "Weight").strip()
    uom = _unit_break_uom_label(unit_type, charge_doc, is_revenue)
    unit_break = flt(applicable.get("unit_break", 0))
    currency = applicable.get("currency") or rate_data.get("currency") or "USD"
    method = rate_data.get("calculation_method") or "Per Unit"
    rate_detail = f"Rate {tier_rate}%"
    if method != "Percentage":
        if original_rate and tier_rate != original_rate:
            rate_detail = (
                f"Rate adjusted from {original_rate} to {tier_rate} {currency}/{uom} "
                f"based on unit break"
            )
        else:
            rate_detail = f"Rate {tier_rate} {currency}/{uom}"
    if method == "Percentage":
        return (
            f"Unit Break ({ut_label}): Value {comparison_qty} {uom} ≥ break {unit_break} {uom} → "
            f"{rate_detail}"
        )
    return (
        f"Unit Break ({ut_label}): Actual {comparison_qty} {uom} ≥ break {unit_break} {uom} → "
        f"{rate_detail}"
    )


def calculate_charge_revenue(charge_doc: Any, parent_doc: Optional[Any] = None) -> Dict:
    """
    Calculate estimated revenue for a charge row.

    Args:
        charge_doc: The charge child document (e.g. Air Booking Charges row)
        parent_doc: Parent document (Air Booking, etc.). If None, derived from charge_doc.parent.

    Returns:
        Dict with keys: amount, calc_notes, success, error
    """
    return _calculate_charge_amount(charge_doc, parent_doc, is_revenue=True)


def calculate_charge_cost(charge_doc: Any, parent_doc: Optional[Any] = None) -> Dict:
    """
    Calculate estimated cost for a charge row.

    Args:
        charge_doc: The charge child document
        parent_doc: Parent document. If None, derived from charge_doc.parent.

    Returns:
        Dict with keys: amount, calc_notes, success, error
    """
    return _calculate_charge_amount(charge_doc, parent_doc, is_revenue=False)


def _calculate_charge_amount(
    charge_doc: Any,
    parent_doc: Optional[Any],
    is_revenue: bool = True,
) -> Dict:
    """Internal: calculate revenue or cost for a charge row. Fills quantity/cost_quantity from parent based on method."""
    _fetch_rates_from_tariff_if_needed(charge_doc)
    result = {
        "amount": 0,
        "calc_notes": "",
        "success": False,
        "error": None,
        "quantity": None,
        "cost_quantity": None,
    }

    parent_doc = _resolve_parent_doc_for_charge(charge_doc, parent_doc)
    parent_doc = _resolve_quantity_context_parent(charge_doc, parent_doc)

    # Internal Transport Order / Declaration Order: revenue = main job charge cost (same item)
    if (
        is_revenue
        and parent_doc
        and getattr(parent_doc, "doctype", None) in ("Transport Order", "Declaration Order")
        and get_service_role(parent_doc) == SERVICE_ROLE_LINKED
    ):
        mt = get_main_service_type(parent_doc)
        mn = get_main_service_name(parent_doc)
        if mt in INTERNAL_JOB_MAIN_JOB_TYPES and mn and frappe.db.exists(mt, mn):
            main_doc = frappe.get_doc(mt, mn)
            item_code = _get_item_code_from_charge(charge_doc)
            cost_amt = _main_job_charge_cost_for_item(main_doc, item_code)
            if cost_amt > 0:
                result["amount"] = cost_amt
                result["calc_notes"] = _("Internal job: revenue = main job ({0} {1}) cost for item {2}").format(
                    mt, mn, item_code or "-"
                )
                result["success"] = True
                return result
            result["amount"] = 0
            result["calc_notes"] = _(
                "Internal job: no actual/estimated cost on main job charge line for item {0} ({1} {2})."
            ).format(item_code or "-", mt, mn)
            result["success"] = True
            return result

    if is_revenue:
        method = _get_field(charge_doc, *REVENUE_METHOD_FIELDS)
        record_type = "Selling"
        unit_type = _get_field(charge_doc, *UNIT_TYPE_FIELDS) or "Weight"
    else:
        method = _get_field(charge_doc, *COST_METHOD_FIELDS)
        record_type = "Cost"
        unit_type = _get_field(charge_doc, *COST_UNIT_TYPE_FIELDS) or "Weight"

    if not method:
        # Internal job Transport / Declaration Order cost: tariff or standard/buying fallback without method
        if (
            not is_revenue
            and parent_doc
            and getattr(parent_doc, "doctype", None) in ("Transport Order", "Declaration Order")
            and get_service_role(parent_doc) == SERVICE_ROLE_LINKED
            and get_main_service_type(parent_doc) in INTERNAL_JOB_MAIN_JOB_TYPES
            and get_main_service_name(parent_doc)
        ):
            std = _item_fallback_buying_or_standard_rate(_get_item_code_from_charge(charge_doc))
            if std > 0:
                cq = flt(getattr(charge_doc, "cost_quantity", None) or getattr(charge_doc, "quantity", None) or 0)
                if cq <= 0:
                    cq = 1.0
                result["amount"] = std * cq
                result["calc_notes"] = _("Internal job cost: standard/buying rate {0} × qty {1}").format(std, cq)
                result["success"] = True
                return result
        result["calc_notes"] = "Charge calculation: No calculation method specified. Set revenue/cost calculation method."
        return result

    actual_data = _get_parent_actual_data(charge_doc, parent_doc)

    # Derive and set quantity from parent based on calculation method
    derived_qty = _get_quantity_for_calculation_method(
        actual_data, method, unit_type, is_revenue=is_revenue
    )

    # Sales Quote / Special Project programme charges: keep row quantity for calculation.
    parent_is_sales_quote = (
        (parent_doc and getattr(parent_doc, "doctype", None) == "Sales Quote")
        or getattr(charge_doc, "parenttype", None) == "Sales Quote"
    )
    parent_is_special_project = (
        (parent_doc and getattr(parent_doc, "doctype", None) == "Special Project")
        or getattr(charge_doc, "parenttype", None) == "Special Project"
    )
    if parent_is_sales_quote or parent_is_special_project:
        row_qty = flt(
            _get_field(charge_doc, "quantity") if is_revenue else _get_field(charge_doc, "cost_quantity")
        )
        if row_qty > 0:
            derived_qty = row_qty
            ut = (unit_type or "Weight").strip().lower()
            actual_data["actual_quantity"] = row_qty
            # Weight Break always uses row qty as estimated weight on quote/programme rows.
            if method == "Weight Break":
                actual_data["actual_weight"] = row_qty
            elif ut == "weight":
                actual_data["actual_weight"] = row_qty
            elif ut == "chargeable weight":
                actual_data["actual_chargeable_weight"] = row_qty
            elif ut == "volume":
                actual_data["actual_volume"] = row_qty
            elif ut in ("piece", "package"):
                actual_data["actual_pieces"] = row_qty
            elif ut == "distance":
                actual_data["actual_distance"] = row_qty
            elif ut == "teu":
                actual_data["actual_teu"] = row_qty
            elif ut == "container":
                actual_data["actual_containers"] = row_qty
            elif ut == "operation time":
                actual_data["actual_operation_time"] = row_qty
            elif ut == "day":
                actual_data["actual_days"] = row_qty
                actual_data["actual_operation_time"] = row_qty
            elif ut == "item count":
                actual_data["actual_item_count"] = row_qty
            elif ut == "handling unit":
                actual_data["actual_handling_units"] = row_qty
            elif ut == "trip":
                actual_data["actual_trips"] = row_qty
            elif ut == "job":
                actual_data["actual_quantity"] = row_qty
            elif ut == "value":
                actual_data["actual_goods_value"] = row_qty
            _spread_row_qty_into_actual_data(actual_data, unit_type, row_qty)

    if is_revenue:
        # Sales Quote / Special Project: keep non-zero row quantity; never push derived 0
        # (parent weight is often missing on quotes — leave qty blank for the user to enter).
        if parent_is_sales_quote or parent_is_special_project:
            if flt(derived_qty) > 0 and (
                getattr(charge_doc, "quantity", None) is None
                or (
                    isinstance(getattr(charge_doc, "quantity", None), (int, float))
                    and flt(charge_doc.quantity) == 0
                )
            ):
                charge_doc.quantity = derived_qty
            row_qty_final = flt(getattr(charge_doc, "quantity", None) or 0)
            if row_qty_final > 0:
                result["quantity"] = row_qty_final
        else:
            charge_doc.quantity = derived_qty
            result["quantity"] = flt(getattr(charge_doc, "quantity", None) or derived_qty)
    else:
        # Sales Quote / Special Project: keep row cost_quantity when already set; never push 0.
        if parent_is_sales_quote or parent_is_special_project:
            if flt(derived_qty) > 0 and (
                getattr(charge_doc, "cost_quantity", None) is None
                or (
                    isinstance(getattr(charge_doc, "cost_quantity", None), (int, float))
                    and flt(charge_doc.cost_quantity) == 0
                )
            ):
                charge_doc.cost_quantity = derived_qty
            row_cost_qty_final = flt(getattr(charge_doc, "cost_quantity", None) or 0)
            if row_cost_qty_final > 0:
                result["cost_quantity"] = row_cost_qty_final
        else:
            charge_doc.cost_quantity = derived_qty
            result["cost_quantity"] = flt(
                getattr(charge_doc, "cost_quantity", None) or derived_qty
            )

    # Weight Break
    if method == "Weight Break":
        applicable = _resolve_weight_break_rate(
            charge_doc,
            actual_data["actual_weight"],
            record_type,
        )
        if not applicable:
            result["calc_notes"] = "Weight Break: No weight break rates defined for this charge"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        _sync_break_tier_rate_to_charge_row(charge_doc, rate, is_revenue)
        weight = actual_data["actual_weight"]
        calc_base = rate * weight
        min_charge = flt(_get_field(charge_doc, "minimum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_minimum_charge") or 0)
        max_charge = flt(_get_field(charge_doc, "maximum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_maximum_charge") or 0)
        amount = calc_base
        if calc_base > 0:
            if min_charge > 0 and amount < min_charge:
                amount = min_charge
            if max_charge > 0 and amount > max_charge:
                amount = max_charge
        else:
            amount = 0.0
        if is_revenue:
            row_currency = getattr(charge_doc, "currency", None) or "USD"
        else:
            row_currency = getattr(charge_doc, "cost_currency", None) or getattr(charge_doc, "currency", None) or "USD"
        currency = applicable.get("currency") or row_currency
        weight_uom = getattr(charge_doc, "uom", None) or getattr(charge_doc, "cost_uom", None) or "Kg"
        weight_break = flt(applicable.get("weight_break", 0))
        detail = (
            f"Weight Break (Weight): Actual weight {weight} {weight_uom} ≥ break {weight_break} {weight_uom} → "
            f"Rate {rate} {currency}/{weight_uom} × {weight} {weight_uom} = {calc_base} {currency}"
        )
        if calc_base > 0 and min_charge > 0 and calc_base < min_charge and amount == min_charge:
            detail += f"; Minimum charge {min_charge} {currency} applied"
        elif max_charge > 0 and calc_base > max_charge and amount == max_charge:
            detail += f"; Maximum charge {max_charge} {currency} applied"
        if amount != calc_base:
            detail += f" (Final: {amount} {currency})"
        result["amount"] = amount
        result["calc_notes"] = detail
        result["success"] = True
        return result

    # Qty Break
    if method == "Qty Break":
        qty = actual_data["actual_pieces"] or actual_data["actual_weight"] or 1
        applicable = _resolve_qty_break_rate(charge_doc, qty, record_type)
        if not applicable:
            result["calc_notes"] = "Qty Break: No qty break rates defined for this charge"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        _sync_break_tier_rate_to_charge_row(charge_doc, rate, is_revenue)
        calc_base = rate * qty
        min_charge = flt(_get_field(charge_doc, "minimum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_minimum_charge") or 0)
        max_charge = flt(_get_field(charge_doc, "maximum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_maximum_charge") or 0)
        amount = calc_base
        if calc_base > 0:
            if min_charge > 0 and amount < min_charge:
                amount = min_charge
            if max_charge > 0 and amount > max_charge:
                amount = max_charge
        else:
            amount = 0.0
        if is_revenue:
            row_currency = getattr(charge_doc, "currency", None) or "USD"
        else:
            row_currency = getattr(charge_doc, "cost_currency", None) or getattr(charge_doc, "currency", None) or "USD"
        currency = applicable.get("currency") or row_currency
        qty_uom = getattr(charge_doc, "uom", None) or getattr(charge_doc, "cost_uom", None) or "Nos"
        qty_break = flt(applicable.get("qty_break", 0))
        detail = (
            f"Qty Break (Piece): Actual qty {qty} {qty_uom} ≥ break {qty_break} {qty_uom} → "
            f"Rate {rate} {currency}/{qty_uom} × {qty} {qty_uom} = {calc_base} {currency}"
        )
        if calc_base > 0 and min_charge > 0 and calc_base < min_charge and amount == min_charge:
            detail += f"; Minimum charge {min_charge} {currency} applied"
        elif max_charge > 0 and calc_base > max_charge and amount == max_charge:
            detail += f"; Maximum charge {max_charge} {currency} applied"
        if amount != calc_base:
            detail += f" (Final: {amount} {currency})"
        result["amount"] = amount
        result["calc_notes"] = detail
        result["success"] = True
        return result

    # Percentage Break: tier by Quantity; amount = (goods_value × %) + minimum_charge (additive)
    if method == "Percentage Break":
        if is_revenue:
            qty = flt(getattr(charge_doc, "quantity", None) or result.get("quantity") or derived_qty or 0)
        else:
            qty = flt(
                getattr(charge_doc, "cost_quantity", None)
                or result.get("cost_quantity")
                or derived_qty
                or 0
            )
        applicable = _resolve_percentage_break_rate(charge_doc, qty, record_type)
        if not applicable:
            result["calc_notes"] = "Percentage Break: No percentage break rates defined for this charge"
            return result
        percentage_rate = flt(applicable.get("percentage_rate", 0))
        _sync_break_tier_rate_to_charge_row(charge_doc, percentage_rate, is_revenue)
        # Prefer parent goods/declared value; fall back to Quantity (also used for tier).
        goods_value = 0.0
        if parent_doc:
            goods_value = flt(
                getattr(parent_doc, "goods_value", None)
                or getattr(parent_doc, "declared_value", None)
                or 0
            )
        if not goods_value:
            goods_value = qty
        pct_amount = goods_value * (percentage_rate / 100.0)
        min_charge = (
            flt(_get_field(charge_doc, "minimum_charge") or 0)
            if is_revenue
            else flt(_get_field(charge_doc, "cost_minimum_charge") or 0)
        )
        max_charge = (
            flt(_get_field(charge_doc, "maximum_charge") or 0)
            if is_revenue
            else flt(_get_field(charge_doc, "cost_maximum_charge") or 0)
        )
        # Minimum charge is additive for Percentage Break (not a floor clamp).
        # Do not surface minimum alone when there is no goods/qty basis yet.
        if pct_amount <= 0 and goods_value <= 0 and qty <= 0:
            calc_base = 0.0
        else:
            calc_base = pct_amount + min_charge
        amount = calc_base
        if max_charge > 0 and amount > max_charge:
            amount = max_charge
        if is_revenue:
            row_currency = getattr(charge_doc, "currency", None) or "USD"
        else:
            row_currency = getattr(charge_doc, "cost_currency", None) or getattr(charge_doc, "currency", None) or "USD"
        currency = applicable.get("currency") or row_currency
        value_break = flt(applicable.get("value_break", 0))
        detail = (
            f"Percentage Break: Qty {qty} ≥ break {value_break} → {percentage_rate}%; "
            f"{percentage_rate}% × goods {goods_value} = {pct_amount}"
        )
        if min_charge:
            detail += f" + minimum {min_charge} = {calc_base} {currency}"
        else:
            detail += f" = {calc_base} {currency}"
        if max_charge > 0 and calc_base > max_charge and amount == max_charge:
            detail += f"; Maximum charge {max_charge} {currency} applied (Final: {amount} {currency})"
        result["amount"] = amount
        result["calc_notes"] = detail
        result["success"] = True
        return result

    # Standard methods via engine
    rate_data = _prepare_rate_data(charge_doc, is_revenue=is_revenue)
    if not rate_data:
        result["calc_notes"] = "Charge calculation: Could not prepare rate data. Check calculation method and unit type."
        return result

    # Use charge-row quantity as the unit-break comparison basis before resolving tiers.
    if is_revenue:
        line_qty = _get_field(charge_doc, "quantity")
    else:
        line_qty = _get_field(charge_doc, "cost_quantity")
    if line_qty is not None and flt(line_qty) > 0:
        _spread_row_qty_into_actual_data(actual_data, unit_type, flt(line_qty))

    unit_break_prefix = _apply_unit_break_to_rate_data(
        charge_doc, rate_data, actual_data, unit_type, record_type, is_revenue
    )
    rate = flt(rate_data.get("rate", 0))
    if not rate and not unit_break_prefix:
        result["calc_notes"] = "Charge calculation: No unit rate specified. Enter rate for this charge."
        return result

    if rate_data.get("calculation_method") == "Percentage":
        base = flt(rate_data.get("base_amount", 0))
        if not base and (unit_type or "").strip().lower() == "value":
            base = flt(actual_data.get("actual_goods_value") or 0)
            if base:
                rate_data["base_amount"] = base
        if not base:
            result["calc_notes"] = "Charge calculation: Base Amount is required for Percentage method. Enter base amount."
            return result

    try:
        engine = RateCalculationEngine()
        res = engine.calculate_rate(rate_data=rate_data, **actual_data)
        if res.get("success"):
            result["amount"] = flt(res.get("amount", 0))
            calc_notes = res.get("calculation_details", "")
            if unit_break_prefix:
                calc_notes = f"{unit_break_prefix}; {calc_notes}" if calc_notes else unit_break_prefix
            result["calc_notes"] = calc_notes
            result["success"] = True
            # Align cost qty with engine when it reports units used (skip Flat Rate etc. where qty is 0)
            if (
                not is_revenue
                and not parent_is_sales_quote
                and res.get("quantity_used") is not None
                and flt(res.get("quantity_used")) > 0
            ):
                charge_doc.cost_quantity = flt(res.get("quantity_used"))
                result["cost_quantity"] = flt(res.get("quantity_used"))
        else:
            result["calc_notes"] = f"Charge calculation failed: {res.get('error', 'Unknown error')}"
            result["error"] = res.get("error")
    except Exception as e:
        frappe.log_error(f"Charge calculation error: {str(e)}")
        result["calc_notes"] = f"Error: {str(e)}"
        result["error"] = str(e)

    # Internal Transport / Declaration Order: after tariff/engine, if cost still zero use Item standard / buying rate
    if (
        not is_revenue
        and parent_doc
        and getattr(parent_doc, "doctype", None) in ("Transport Order", "Declaration Order")
        and get_service_role(parent_doc) == SERVICE_ROLE_LINKED
        and flt(result.get("amount", 0)) <= 0
    ):
        mt = get_main_service_type(parent_doc)
        mn = get_main_service_name(parent_doc)
        if mt in INTERNAL_JOB_MAIN_JOB_TYPES and mn:
            std = _item_fallback_buying_or_standard_rate(_get_item_code_from_charge(charge_doc))
            if std > 0:
                cq = flt(result.get("cost_quantity") or getattr(charge_doc, "cost_quantity", None) or 0)
                if cq <= 0:
                    cq = flt(getattr(charge_doc, "quantity", None) or 0) or 1.0
                result["amount"] = std * cq
                result["calc_notes"] = _("Internal job cost: standard/buying rate {0} × qty {1}").format(std, cq)
                result["success"] = True
                result["error"] = None

    return result


# Charge doctypes that use centralized calculation (for client-side recalculation API)
CHARGE_DOCTYPES = (
    "Sales Quote Charge",
    "Change Request Charge",
    "Transport Order Charges",
    "Transport Job Charges",
    "Air Booking Charges",
    "Air Shipment Charges",
    "Sea Booking Charges",
    "Sea Shipment Charges",
    "Sea Consolidation Charges",
    "Air Consolidation Charges",
    "Special Project Charges",
    "Declaration Charges",
    "Declaration Order Charges",
)

# Disbursement: copy cost-side inputs to revenue-side (pass-through billing).
# Revenue mirrors cost for: calculation method, unit rate/cost, unit type, quantity, UOM, currency,
# minimum qty/rate/charges, max charge, base amount/qty, tariffs (where fields exist per doctype).
# Bill To and Pay To stay independent: _mirror_disbursement_cost_to_revenue skips those field names.
_AIR_BOOKING_DISBURSEMENT_PAIRS = (
    ("cost_calculation_method", "revenue_calculation_method"),
    ("cost_quantity", "quantity"),
    ("cost_uom", "uom"),
    ("cost_currency", "currency"),
    ("unit_cost", "unit_rate"),
    ("cost_unit_type", "unit_type"),
    ("cost_minimum_quantity", "minimum_quantity"),
    ("cost_minimum_unit_rate", "minimum_unit_rate"),
    ("cost_minimum_charge", "minimum_charge"),
    ("cost_maximum_charge", "maximum_charge"),
    ("cost_base_amount", "base_amount"),
    ("cost_base_quantity", "base_quantity"),
    ("use_tariff_in_cost", "use_tariff_in_revenue"),
    ("cost_tariff", "revenue_tariff"),
)

_CHANGE_REQUEST_DISBURSEMENT_PAIRS = (
    ("cost_calculation_method", "calculation_method"),
)

_SALES_QUOTE_CHARGE_DISBURSEMENT_PAIRS = (
    ("cost_calculation_method", "revenue_calculation_method"),
    ("cost_quantity", "quantity"),
    ("cost_uom", "uom"),
    ("cost_currency", "currency"),
    ("unit_cost", "unit_rate"),
    ("cost_unit_type", "unit_type"),
    ("cost_minimum_quantity", "minimum_quantity"),
    ("cost_minimum_charge", "minimum_charge"),
    ("cost_maximum_charge", "maximum_charge"),
    ("cost_base_amount", "base_amount"),
    ("use_tariff_in_cost", "use_tariff_in_revenue"),
    ("cost_tariff", "revenue_tariff"),
)

DISBURSEMENT_FIELD_MAP = {
    "Sales Quote Charge": _SALES_QUOTE_CHARGE_DISBURSEMENT_PAIRS,
    "Change Request Charge": _CHANGE_REQUEST_DISBURSEMENT_PAIRS,
    "Transport Order Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS,
    "Transport Job Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS
    + (("buying_currency", "selling_currency"),),
    "Air Booking Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS,
    "Air Shipment Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS,
    "Sea Booking Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS,
    "Declaration Order Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS,
    "Sea Shipment Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS
    + (("buying_currency", "selling_currency"),),
    "Special Project Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS
    + (("buying_currency", "selling_currency"),),
    "Declaration Charges": _AIR_BOOKING_DISBURSEMENT_PAIRS
    + (("buying_currency", "selling_currency"),),
}


# Fields cleared when charge_type locks the cost or revenue side (meta-driven per DocType).
CHARGE_COST_SIDE_CLEAR_FIELDS = (
    "cost_calculation_method",
    "unit_cost",
    "cost_unit_type",
    "cost_currency",
    "cost_quantity",
    "cost_uom",
    "cost_minimum_quantity",
    "cost_minimum_unit_rate",
    "cost_minimum_charge",
    "cost_maximum_charge",
    "cost_base_amount",
    "cost_base_quantity",
    "use_tariff_in_cost",
    "cost_tariff",
    "cost_sheet_source",
    "buying_currency",
    "estimated_cost",
    "cost_calc_notes",
    "actual_cost",
)

CHARGE_REVENUE_SIDE_CLEAR_FIELDS = (
    "revenue_calculation_method",
    "calculation_method",
    "unit_rate",
    "unit_type",
    "currency",
    "quantity",
    "uom",
    "minimum_quantity",
    "minimum_unit_rate",
    "minimum_charge",
    "maximum_charge",
    "base_amount",
    "base_quantity",
    "use_tariff_in_revenue",
    "revenue_tariff",
    "tariff",
    "selling_currency",
    "estimated_revenue",
    "revenue_calc_notes",
    "actual_revenue",
)

_CHARGE_BREAK_DOCTYPES = (
    "Sales Quote Weight Break",
    "Sales Quote Qty Break",
    "Sales Quote Percentage Break",
    "Charge Unit Break",
)


def _reset_charge_field_for_cleanup(meta: Any, fieldname: str) -> Any:
    df = meta.get_field(fieldname)
    if not df:
        return None
    ft = df.fieldtype
    if ft in ("Currency", "Float", "Int", "Percent"):
        return 0
    if ft == "Check":
        return 0
    if ft in ("Link", "Select", "Dynamic Link"):
        return None
    return ""


def _clear_charge_side_fields(doc: Any, fieldnames: Tuple[str, ...]) -> None:
    meta = frappe.get_meta(doc.doctype)
    for fieldname in fieldnames:
        if not meta.get_field(fieldname):
            continue
        setattr(doc, fieldname, _reset_charge_field_for_cleanup(meta, fieldname))


def _clear_cost_side(doc: Any) -> None:
    _clear_charge_side_fields(doc, CHARGE_COST_SIDE_CLEAR_FIELDS)


def _clear_revenue_side(doc: Any) -> None:
    _clear_charge_side_fields(doc, CHARGE_REVENUE_SIDE_CLEAR_FIELDS)


def _clear_charge_break_rows(doctype: str, name: Optional[str], break_type: str) -> None:
    if not doctype or not name or str(name).startswith("new"):
        return
    filters = {
        "reference_doctype": doctype,
        "reference_no": name,
        "type": break_type,
    }
    for break_dt in _CHARGE_BREAK_DOCTYPES:
        if frappe.db.exists("DocType", break_dt):
            frappe.db.delete(break_dt, filters)


OPERATIONAL_CHARGE_TYPES = frozenset({"Margin", "Disbursement", "Revenue", "Cost"})


def normalize_operational_charge_type(charge_type: str | None, default: str = "Margin") -> str:
	"""Map Sales Quote ``Other`` (and other non-operational values) to a valid job charge type."""
	ct = (charge_type or "").strip()
	if ct in OPERATIONAL_CHARGE_TYPES:
		return ct
	fallback = (default or "Margin").strip()
	return fallback if fallback in OPERATIONAL_CHARGE_TYPES else "Margin"


def normalize_operational_charge_rows_on_parent(parent_doc: Any, charges_field: str = "charges") -> int:
	"""Normalize ``charge_type`` on operational charge child rows before parent save validation."""
	if not parent_doc:
		return 0
	changed = 0
	for row in parent_doc.get(charges_field) or []:
		if not hasattr(row, "charge_type"):
			continue
		current = (getattr(row, "charge_type", None) or "").strip()
		normalized = normalize_operational_charge_type(current)
		if normalized != current:
			row.charge_type = normalized
			changed += 1
	return changed


def apply_charge_type_side_cleanup(doc: Any) -> bool:
    """
    When charge_type is Revenue or Cost, clear inputs on the locked side and linked breaks.
    Mutates doc in place. Returns True if cleanup ran.
    """
    charge_type = (getattr(doc, "charge_type", None) or "").strip()
    if charge_type == "Revenue":
        _clear_cost_side(doc)
        _clear_charge_break_rows(getattr(doc, "doctype", None), getattr(doc, "name", None), "Cost")
        return True
    if charge_type == "Cost":
        _clear_revenue_side(doc)
        _clear_charge_break_rows(getattr(doc, "doctype", None), getattr(doc, "name", None), "Selling")
        return True
    return False


def compute_charge_row_estimates(doc: Any, parent_doc: Optional[Any] = None) -> None:
    """
    Apply charge_type side cleanup, then calculate estimated revenue/cost (and notes).
    Standard pattern for quote/booking charge child validate.
    """
    apply_charge_type_side_cleanup(doc)
    if apply_disbursement_charge_calculation_if_applicable(doc, parent_doc):
        return
    rev = calculate_charge_revenue(doc, parent_doc)
    if hasattr(doc, "estimated_revenue"):
        doc.estimated_revenue = _estimated_display_amount(doc, rev.get("amount", 0), is_revenue=True)
    if hasattr(doc, "revenue_calc_notes"):
        doc.revenue_calc_notes = rev.get("calc_notes", "")
    elif hasattr(doc, "calculation_notes") and rev.get("calc_notes"):
        doc.calculation_notes = rev.get("calc_notes", "")

    cost = calculate_charge_cost(doc, parent_doc)
    if hasattr(doc, "estimated_cost"):
        doc.estimated_cost = _estimated_display_amount(doc, cost.get("amount", 0), is_revenue=False)
    if hasattr(doc, "cost_calc_notes"):
        doc.cost_calc_notes = cost.get("calc_notes", "")
    elif hasattr(doc, "calculation_notes") and cost.get("calc_notes") and not rev.get("calc_notes"):
        doc.calculation_notes = cost.get("calc_notes", "")


def _mirror_disbursement_cost_to_revenue(doc: Any, doctype: str) -> Dict[str, Any]:
    pairs = DISBURSEMENT_FIELD_MAP.get(doctype)
    if not pairs:
        return {}
    meta = frappe.get_meta(doctype)
    out: Dict[str, Any] = {}
    for src, tgt in pairs:
        if src in ("pay_to", "bill_to") or tgt in ("pay_to", "bill_to"):
            continue
        if not meta.get_field(src) or not meta.get_field(tgt):
            continue
        val = getattr(doc, src, None)
        setattr(doc, tgt, val)
        out[tgt] = val
    return out


def apply_disbursement_charge_calculation_if_applicable(doc: Any, parent_doc: Optional[Any] = None) -> bool:
    """
    For Disbursement charges: mirror cost→revenue, run cost engine only, sync amounts and notes.
    Mutates doc in place. Used by child validate/recalculate so server matches calculate_charge_row.
    Returns True if the doc was handled (caller should skip normal revenue+cost calculation).
    """
    doctype = getattr(doc, "doctype", None)
    if getattr(doc, "charge_type", None) != "Disbursement" or not doctype:
        return False
    if doctype not in DISBURSEMENT_FIELD_MAP:
        return False
    _mirror_disbursement_cost_to_revenue(doc, doctype)
    cost = calculate_charge_cost(doc, parent_doc)
    _mirror_disbursement_cost_to_revenue(doc, doctype)
    est_cost = flt(cost.get("amount", 0))
    notes = cost.get("calc_notes", "") or ""

    if doctype in (
        "Transport Job Charges",
        "Air Shipment Charges",
        "Sea Shipment Charges",
        "Special Project Charges",
        "Declaration Charges",
    ):
        if hasattr(doc, "actual_revenue"):
            doc.actual_revenue = est_cost
        if hasattr(doc, "actual_cost"):
            doc.actual_cost = est_cost
        if hasattr(doc, "estimated_revenue"):
            doc.estimated_revenue = est_cost
        if hasattr(doc, "estimated_cost"):
            doc.estimated_cost = est_cost
        if hasattr(doc, "revenue_calc_notes"):
            doc.revenue_calc_notes = notes
        if hasattr(doc, "cost_calc_notes"):
            doc.cost_calc_notes = notes
        elif hasattr(doc, "calculation_notes"):
            doc.calculation_notes = notes
        return True

    if hasattr(doc, "estimated_revenue"):
        doc.estimated_revenue = est_cost
    if hasattr(doc, "estimated_cost"):
        doc.estimated_cost = est_cost
    if hasattr(doc, "revenue_calc_notes"):
        doc.revenue_calc_notes = notes
    if hasattr(doc, "cost_calc_notes"):
        doc.cost_calc_notes = notes
    elif hasattr(doc, "calculation_notes"):
        doc.calculation_notes = notes
    return True


@frappe.whitelist()
def calculate_charge_row(
    doctype: str,
    parenttype: str,
    parent: str,
    row_data: str,
    parent_overrides: Optional[str] = None,
):
    """
    Recalculate estimated_revenue, estimated_cost, actual_revenue, and actual_cost for a charge row.
    Used by client-side form events when user changes rate (or unit_rate on quote rows), calculation_method, etc.
    Actual amounts use the same calculation method; when separate actual-value inputs exist they are used.

    Args:
        doctype: Charge child doctype (e.g. 'Air Booking Charges')
        parenttype: Parent doctype (e.g. 'Air Booking')
        parent: Parent document name
        row_data: JSON string of the charge row data (or dict)

    Returns:
        dict with estimated_revenue, estimated_cost, actual_revenue, actual_cost, revenue_calc_notes, cost_calc_notes
    """
    import json

    if doctype not in CHARGE_DOCTYPES:
        return {"success": False, "error": f"Unsupported doctype: {doctype}"}

    try:
        if isinstance(row_data, str):
            row_dict = json.loads(row_data)
        else:
            row_dict = row_data

        doc = frappe.new_doc(doctype)
        doc.update(row_dict)
        doc.parenttype = parenttype
        doc.parent = parent

        parent_doc = None
        # Skip loading parent when it's a temporary name (unsaved document)
        if parent and parent not in ("new", "") and not str(parent).startswith("new-"):
            try:
                parent_doc = frappe.get_doc(parenttype, parent)
            except Exception:
                pass
        if parent_doc and parenttype == "Change Request" and doctype == "Change Request Charge":
            from logistics.utils.sales_quote_charge_parameters import (
                resolve_change_request_charge_parameters,
            )

            resolved = resolve_change_request_charge_parameters(doc, parent_doc)
            if resolved:
                doc.update(resolved)
        if parent_doc and parent_overrides and parenttype != "Sales Quote":
            _apply_charge_parent_overrides(parent_doc, parent_overrides)

        apply_charge_type_side_cleanup(doc)

        charge_type = getattr(doc, "charge_type", None) or row_dict.get("charge_type")
        if charge_type == "Disbursement":
            # Mirror cost -> revenue before cost engine runs, then again after (engine may update cost_quantity etc.)
            _mirror_disbursement_cost_to_revenue(doc, doctype)
            cost = calculate_charge_cost(doc, parent_doc)
            disbursement_mirror = _mirror_disbursement_cost_to_revenue(doc, doctype)
            est_cost = _estimated_display_amount(doc, cost.get("amount", 0), is_revenue=False)
            est_rev = est_cost
            notes = cost.get("calc_notes", "")
            actual_cst = (
                flt(row_dict.get("actual_cost"))
                if row_dict.get("actual_cost") is not None
                else est_cost
            )
            actual_rev = actual_cst
            cq = cost.get("cost_quantity")
            cq_f = flt(cq) if cq is not None else None
            return {
                "success": True,
                "estimated_revenue": est_rev,
                "estimated_cost": est_cost,
                "actual_revenue": actual_rev,
                "actual_cost": actual_cst,
                "revenue_calc_notes": notes,
                "cost_calc_notes": notes,
                "quantity": cq_f,
                "cost_quantity": cq_f,
                "disbursement_mirror": disbursement_mirror,
                "row_updates": _charge_row_sync_dict_for_client(doc),
            }

        rev = calculate_charge_revenue(doc, parent_doc)
        cost = calculate_charge_cost(doc, parent_doc)
        est_rev = _estimated_display_amount(doc, rev.get("amount", 0), is_revenue=True)
        est_cost = _estimated_display_amount(doc, cost.get("amount", 0), is_revenue=False)
        # Actual = same calculation (basis for SI/PI); override with actual-value inputs when present
        actual_rev = flt(row_dict.get("actual_revenue")) if row_dict.get("actual_revenue") is not None else est_rev
        actual_cst = flt(row_dict.get("actual_cost")) if row_dict.get("actual_cost") is not None else est_cost

        out = {
            "success": True,
            "estimated_revenue": est_rev,
            "estimated_cost": est_cost,
            "actual_revenue": actual_rev,
            "actual_cost": actual_cst,
            "revenue_calc_notes": rev.get("calc_notes", ""),
            "cost_calc_notes": cost.get("calc_notes", ""),
            "disbursement_mirror": None,
            "row_updates": _charge_row_sync_dict_for_client(doc),
        }
        # Omit qty keys when unset so the client does not clear blank estimate fields.
        if rev.get("quantity") is not None:
            out["quantity"] = rev.get("quantity")
        if cost.get("cost_quantity") is not None:
            out["cost_quantity"] = cost.get("cost_quantity")
        return out
    except Exception as e:
        frappe.log_error(f"Charge row calculation error: {str(e)}")
        return {"success": False, "error": str(e)}
