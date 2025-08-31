# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseJob(Document):
	pass

from frappe.utils import flt, now_datetime

# --- Helpers ---------------------------------------------------------------

def _get_last_qty(item, location, handling_unit=None, serial_no=None, batch_no=None):
    # Normalize Nones so we can use IFNULL(...) equality in SQL
    params = {
        "item": item,
        "location": location,
        "handling_unit": handling_unit or "",
        "serial_no": serial_no or "",
        "batch_no": batch_no or "",
    }
    row = frappe.db.sql(
        """
        SELECT end_qty
        FROM `tabWarehouse Stock Ledger`
        WHERE item = %(item)s
          AND storage_location = %(location)s
          AND IFNULL(handling_unit,'') = %(handling_unit)s
          AND IFNULL(serial_no,'') = %(serial_no)s
          AND IFNULL(batch_no,'') = %(batch_no)s
        ORDER BY posting_date DESC, creation DESC
        LIMIT 1
        """,
        params,
        as_dict=True,
    )
    return flt(row[0].end_qty) if row else 0.0


def _make_ledger_row(job, ji, delta_qty, beg_qty, end_qty, posting_dt):
    led = frappe.new_doc("Warehouse Stock Ledger")

    # New fields
    led.posting_date = posting_dt
    led.warehouse_job = job.name

    # Key fields
    led.item = ji.item
    led.storage_location = ji.location
    led.handling_unit = getattr(ji, "handling_unit", None)
    led.serial_no = getattr(ji, "serial_no", None)
    led.batch_no = getattr(ji, "batch_no", None)

    # Quantities (note: field name is 'quantiy' in the DocType)
    led.quantiy = delta_qty
    led.beg_quantity = beg_qty
    led.end_qty = end_qty

    led.insert(ignore_permissions=True)


# --- Controller ------------------------------------------------------------

class WarehouseJob(Document):
    def on_submit(self):
        job_type = (getattr(self, "type", "") or "").strip()
        if job_type not in ("Putaway", "Pick"):
            frappe.throw("Warehouse Job type must be either <b>Putaway</b> or <b>Pick</b>.")

        if not getattr(self, "items", None):
            frappe.throw("No items to post to the Warehouse Stock Ledger.")

        sign = 1 if job_type == "Putaway" else -1
        posting_dt = now_datetime()

        for ji in self.items:
            if not ji.location:
                frappe.throw(f"Row #{ji.idx}: Location is required.")
            if not ji.item:
                frappe.throw(f"Row #{ji.idx}: Item is required.")
            qty = flt(ji.quantity)
            if qty <= 0:
                frappe.throw(f"Row #{ji.idx}: Quantity must be greater than zero.")

            delta = sign * qty

            beg = _get_last_qty(
                item=ji.item,
                location=ji.location,
                handling_unit=getattr(ji, "handling_unit", None),
                serial_no=getattr(ji, "serial_no", None),
                batch_no=getattr(ji, "batch_no", None),
            )
            end = beg + delta

            if end < 0:
                frappe.throw(
                    f"Row #{ji.idx}: Insufficient stock to Pick {qty}. "
                    f"Beginning qty: {beg}, would end at {end}."
                )

            _make_ledger_row(self, ji, delta, beg, end, posting_dt)
