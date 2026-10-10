# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Which Periodic Billing charges can also post internal or intercompany billing.

The customer invoice always uses the selected charge lines. A line is also an
internal or intercompany candidate when its Warehouse Job is a linked service
and the job company is compared with the main service company. Amounts stay on
the Periodic Billing line. They are not taken from the warehouse job charge table.
"""

from __future__ import annotations

from logistics.intercompany.invoice_guard import relationship_for_companies


def charge_amount(charge: dict) -> float:
	"""Billable amount on one Periodic Billing charge row."""
	total = _flt(charge.get("total"))
	if total:
		return total
	return _flt(charge.get("quantity")) * _flt(charge.get("rate"))


def invoice_line_from_charge(charge: dict) -> dict | None:
	"""Sales or purchase invoice item built from a Periodic Billing charge."""
	item_code = (charge.get("item_code") or "").strip()
	if not item_code:
		return None
	quantity = _flt(charge.get("quantity"))
	amount = charge_amount(charge)
	if not amount:
		return None
	if not quantity:
		quantity = 1.0
	rate = amount / quantity
	return {
		"item_code": item_code,
		"item_name": charge.get("item_name") or item_code,
		"description": charge.get("description") or charge.get("item_name") or item_code,
		"qty": quantity or 0.0,
		"rate": rate or 0.0,
		"uom": charge.get("uom") or None,
	}


def classify_periodic_billing_charges(
	charges,
	jobs,
	*,
	intercompany_enabled: bool,
	relationships,
) -> dict:
	"""Classify each charge and say which optional postings the dialog can offer."""
	jobs = jobs or {}
	classified = []
	different_company_jobs = False
	for charge in charges or []:
		row = dict(charge)
		row["amount"] = charge_amount(charge)
		row["line"] = invoice_line_from_charge(charge)
		row["posting"] = ""
		row["relationship"] = None
		job_name = (charge.get("warehouse_job") or "").strip()
		job = jobs.get(job_name) if job_name else None
		if job and row["line"] and row["amount"] > 0 and _is_linked(job):
			operating = (job.get("company") or "").strip()
			main_company = (job.get("main_company") or "").strip()
			row["operating_company"] = operating
			row["main_company"] = main_company
			row["main_service_type"] = job.get("main_service_type") or ""
			row["main_service"] = job.get("main_service") or ""
			if operating and main_company and operating == main_company:
				row["posting"] = "internal"
			elif operating and main_company and operating != main_company:
				different_company_jobs = True
				if intercompany_enabled:
					row["posting"] = "intercompany"
					row["relationship"] = relationship_for_companies(
						relationships, main_company, operating
					)
		classified.append(row)

	return {
		"charges": classified,
		"show_internal_billing": any(row["posting"] == "internal" for row in classified),
		"show_intercompany": any(row["posting"] == "intercompany" for row in classified),
		"intercompany_disabled": bool(different_company_jobs and not intercompany_enabled),
	}


def groups_for_selection(classified_charges, selected_idxs) -> dict:
	"""Split the checked charge lines into the customer invoice and optional postings."""
	selected = {int(idx) for idx in (selected_idxs or [])}
	customer_lines = []
	internal: dict[str, dict] = {}
	intercompany: dict[str, dict] = {}
	for row in classified_charges or []:
		if int(row.get("idx") or 0) not in selected:
			continue
		line = row.get("line")
		if line:
			customer_lines.append(line)
		posting = row.get("posting") or ""
		if posting not in ("internal", "intercompany"):
			continue
		job_name = (row.get("warehouse_job") or "").strip()
		if not job_name:
			continue
		bucket = internal if posting == "internal" else intercompany
		group = bucket.get(job_name)
		if not group:
			relationship = row.get("relationship") or {}
			group = {
				"warehouse_job": job_name,
				"operating_company": row.get("operating_company") or "",
				"main_company": row.get("main_company") or "",
				"main_service_type": row.get("main_service_type") or "",
				"main_service": row.get("main_service") or "",
				"internal_customer": relationship.get("internal_customer") or "",
				"internal_supplier": relationship.get("internal_supplier") or "",
				"lines": [],
			}
			bucket[job_name] = group
		group["lines"].append(line)
	return {
		"customer_lines": customer_lines,
		"internal": list(internal.values()),
		"intercompany": list(intercompany.values()),
	}


def _is_linked(job: dict) -> bool:
	return bool(
		job.get("is_linked")
		and (job.get("main_service_type") or "").strip()
		and (job.get("main_service") or "").strip()
		and (job.get("main_company") or "").strip()
		and (job.get("company") or "").strip()
	)


def _flt(value) -> float:
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0
