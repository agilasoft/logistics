# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ReleaseOrder(Document):
	pass

from frappe.utils import nowdate

class ReleaseOrder(Document):
    pass


@frappe.whitelist()
def prepare_warehouse_job_from_release_order(release_order: str):
    """
    Prepare (but do not save) a Warehouse Job (type = Pick) from a Release Order.
    Always copies charges.
    """
    if not release_order:
        frappe.throw("Release Order is required.")

    ro = frappe.get_doc("Release Order", release_order)

    wj = frappe.new_doc("Warehouse Job")
    wj.naming_series = "WJ-.########"
    wj.type = "Pick"
    wj.job_open_date = nowdate()
    wj.reference_order_type = "Release Order"
    wj.reference_order = ro.name

    # Map items
    for r in ro.get("items", []):
        it = wj.append("items", {})
        it.location = getattr(r, "location", None)
        it.handling_unit = getattr(r, "handling_unit", None)
        it.item = getattr(r, "item_code", None)
        it.quantity = getattr(r, "qty", 1)
        it.serial_no = getattr(r, "serial_no", None)
        it.batch_no = getattr(r, "batch_no", None)

    # Always copy charges
    for ch in ro.get("charges", []):
        row = wj.append("table_dxtc", {})
        row.item_code = getattr(ch, "item_code", None)
        row.item_name = getattr(ch, "item_name", None)
        row.uom = getattr(ch, "uom", None)
        row.quantity = getattr(ch, "quantity", 1)
        row.currency = getattr(ch, "currency", None)
        row.rate = getattr(ch, "rate", 0)
        row.total = getattr(ch, "total", row.quantity * row.rate)

    return wj.as_dict()
