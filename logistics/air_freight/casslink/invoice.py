# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Group CASS billing lines and create draft Purchase Invoices."""

from __future__ import unicode_literals

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import flt, today

from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict


def _get(line, field, default=None):
	if isinstance(line, dict):
		return line.get(field, default)
	return getattr(line, field, default)


def group_lines_for_invoice(lines: Iterable[Any]) -> Tuple[Dict[Tuple[str, str], List[Any]], List[Tuple[Any, str]]]:
	"""Split lines into (supplier, currency) batches.

	Skipped reasons: already_invoiced, unmatched, no_supplier.
	"""
	batches: Dict[Tuple[str, str], List[Any]] = defaultdict(list)
	skipped: List[Tuple[Any, str]] = []
	for line in lines:
		if _get(line, "purchase_invoice"):
			skipped.append((line, "already_invoiced"))
			continue
		if (_get(line, "match_status") or "") != "Matched":
			skipped.append((line, "unmatched"))
			continue
		supplier = _get(line, "supplier")
		if not supplier:
			skipped.append((line, "no_supplier"))
			continue
		currency = (_get(line, "currency") or "") or ""
		batches[(supplier, currency)].append(line)
	return dict(batches), skipped


def create_draft_purchase_invoices(period_name: str) -> Dict[str, Any]:
	period = frappe.get_doc("CASS Settlement Period", period_name)
	settings = _settings_for_company(period.company)
	item_code = getattr(settings, "cass_charge_item", None) if settings else None
	if not item_code:
		frappe.throw(_("Set CASS Charge Item on IATA Settings before creating Purchase Invoices."))
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("CASS Charge Item {0} does not exist").format(item_code))

	lines = _collect_period_lines(period_name)
	batches, skipped = group_lines_for_invoice(lines)
	created = []
	for (supplier, currency), batch in batches.items():
		pi_name = _insert_purchase_invoice(period, supplier, currency, batch, item_code)
		created.append(pi_name)
		_mark_lines_invoiced(batch, pi_name)

	period.reload()
	period.recompute_totals()
	if created and not any(reason == "unmatched" for _line, reason in skipped):
		if period.status not in ("Closed",):
			period.status = "Invoiced"
	period.save(ignore_permissions=True)
	return {
		"purchase_invoices": created,
		"invoiced_lines": sum(len(b) for b in batches.values()),
		"skipped": len(skipped),
		"skipped_no_supplier": sum(1 for _l, reason in skipped if reason == "no_supplier"),
		"skipped_unmatched": sum(1 for _l, reason in skipped if reason == "unmatched"),
	}


def _collect_period_lines(period_name: str) -> List[Any]:
	files = frappe.get_all(
		"CASS File",
		filters={"settlement_period": period_name},
		pluck="name",
	)
	lines = []
	for name in files:
		doc = frappe.get_doc("CASS File", name)
		for row in doc.billing_lines or []:
			row._cass_file = name
			lines.append(row)
	return lines


def _mark_lines_invoiced(batch, pi_name: str):
	for line in batch:
		file_name = getattr(line, "_cass_file", None) or getattr(line, "parent", None)
		if not file_name or not getattr(line, "name", None):
			continue
		frappe.db.set_value(
			"CASS Billing Line",
			line.name,
			{"match_status": "Invoiced", "purchase_invoice": pi_name},
			update_modified=False,
		)


def _insert_purchase_invoice(period, supplier: str, currency: str, batch, item_code: str) -> str:
	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = supplier
	pi.company = period.company
	pi.posting_date = today()
	pi.ignore_pricing_rule = 1
	if currency and frappe.get_meta("Purchase Invoice").has_field("currency"):
		pi.currency = currency
	pi_meta = frappe.get_meta("Purchase Invoice")
	if pi_meta.get_field("reference_doctype"):
		pi.reference_doctype = "CASS Settlement Period"
		pi.reference_name = period.name
	refs = sorted(
		{
			(_get(line, "billing_reference") or "").strip()
			for line in batch
			if _get(line, "billing_reference")
		}
	)
	if len(refs) == 1 and pi_meta.get_field("bill_no"):
		pi.bill_no = refs[0]
	pi.remarks = _("Draft CASS airline bill from {0}").format(period.name)

	pi_item_meta = frappe.get_meta("Purchase Invoice Item")
	has_ref = pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name")

	for line in batch:
		awb = _get(line, "awb_display") or _get(line, "awb_number") or ""
		airline = _get(line, "airline") or _get(line, "airline_prefix") or ""
		reference = _get(line, "billing_reference") or ""
		if awb:
			description = _("CASS AWB {0}").format(awb)
		elif reference:
			description = _("CASS {0} invoice {1}").format(airline, reference)
		else:
			description = _("CASS airline bill {0}").format(airline)
		row = pi.append(
			"items",
			{
				"item_code": item_code,
				"qty": 1,
				"rate": flt(_get(line, "amount")),
				"description": description,
			},
		)
		shipment = _get(line, "air_shipment")
		if has_ref and shipment:
			row.reference_doctype = "Air Shipment"
			row.reference_name = shipment
		job_number = None
		if shipment:
			job_number = frappe.db.get_value("Air Shipment", shipment, "job_number")
		if job_number:
			for k, v in reference_dimension_row_dict(
				"Purchase Invoice Item", "Job Number", job_number
			).items():
				setattr(row, k, v)

	pi.set_missing_values()
	pi.insert(ignore_permissions=True)
	return pi.name


def _settings_for_company(company: Optional[str]):
	from logistics.air_freight.utils.iata_settings_utils import get_settings

	return get_settings(company=company)
