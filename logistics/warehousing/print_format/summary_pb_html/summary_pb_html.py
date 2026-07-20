"""Helpers for Summary PB HTML (FC00B1-style) Periodic Billing print format.

Main table rows track Putaway (inbound) / Pick (outbound) Warehouse Jobs
within the Periodic Billing date_from–date_to window:
  FROM / TO / NO. OF DAYS = job activity span
  INBOUND / OUTBOUND      = handling-unit qty for that job
  BALANCE                 = running pallet balance after the movement
  PHP / TOTAL             = storage rate × balance × days

OTHER CHARGES aggregates non-storage Periodic Billing charge lines
(Handling In/Out items flagged custom_inbound_charge / custom_outbound_charge, etc.).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Set

import frappe
from frappe.utils import cint, flt, formatdate, getdate


@frappe.whitelist()
def get_summary_pb_print_data(name: str) -> Dict[str, Any]:
	"""Build row data for the Summary PB HTML print format."""
	if not name:
		frappe.throw("Periodic Billing name is required")

	doc = frappe.get_doc("Periodic Billing", name)
	storage_rate = _storage_rate(doc)
	opening = _opening_balance(doc)
	activity_rows = _build_activity_rows(doc, storage_rate, opening)
	other_rows = _build_other_charge_rows(doc, start_no=len(activity_rows) + 1)

	activity_subtotal = flt(sum(flt(r.get("total") or 0) for r in activity_rows), 2)
	other_subtotal = flt(sum(flt(r.get("total") or 0) for r in other_rows), 2)
	subtotal = flt(activity_subtotal + other_subtotal, 2)
	vat_amount = flt(subtotal * 0.12, 2)
	grand_total = flt(subtotal + vat_amount, 2)

	customer_name = ""
	if doc.customer:
		customer_name = (
			frappe.db.get_value("Customer", doc.customer, "customer_name") or doc.customer
		)

	period_label = _period_label(doc.date_from, doc.date_to)
	last_month = {
		"date": formatdate(doc.date_from, "dd-MM-yyyy") if doc.date_from else "",
		"balance": opening,
	}

	prepared_name = ""
	if doc.owner:
		prepared_name = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner

	location = ""
	if doc.branch:
		location = frappe.db.get_value("Branch", doc.branch, "branch") or doc.branch

	company_name = doc.company or ""
	if doc.company and frappe.db.exists("Company", doc.company):
		company_name = frappe.db.get_value("Company", doc.company, "company_name") or doc.company

	return {
		"name": doc.name,
		"customer": doc.customer,
		"customer_name": customer_name,
		"company_name": company_name,
		"location": location or "LOGISTICS CENTER",
		"form_code": "FC00B1",
		"revision_date": "",
		"period_label": period_label,
		"date_from": str(doc.date_from) if doc.date_from else "",
		"date_to": str(doc.date_to) if doc.date_to else "",
		"last_month_date": last_month.get("date") or "",
		"last_month_balance": last_month.get("balance"),
		"storage_rows": activity_rows,
		"other_rows": other_rows,
		"subtotal": subtotal,
		"vat_rate_pct": 12,
		"vat_amount": vat_amount,
		"grand_total": grand_total,
		"prepared_by": prepared_name,
		"prepared_role": "",
		"checked_by": "",
		"checked_role": "",
		"noted_by": "",
		"noted_role": "",
		"special_remarks": "",
	}


# ---------------------------------------------------------------------------
# Activity rows (main table)
# ---------------------------------------------------------------------------


def _build_activity_rows(
	doc, storage_rate: float, opening_balance: float
) -> List[Dict[str, Any]]:
	"""One row per Putaway/Pick job in the billing period (FC00B1 tracking)."""
	jobs = _jobs_for_period(doc)
	if not jobs:
		return _fallback_storage_rows(doc, storage_rate)

	balance = flt(opening_balance)
	rows: List[Dict[str, Any]] = []
	for idx, job in enumerate(jobs, start=1):
		day_from, day_to = _job_date_span(job)
		days = _inclusive_days(day_from, day_to)
		inbound = ""
		outbound = ""
		qty = flt(job.get("qty") or 0)

		job_type = (job.get("type") or "").strip()
		if job_type == "Putaway":
			inbound = qty
			balance = flt(balance + qty)
		elif job_type == "Pick":
			outbound = qty
			balance = flt(balance - qty)

		line_total = flt(balance * days * storage_rate, 2) if storage_rate else 0.0
		remarks = job.get("name") or ""
		rows.append(
			{
				"no": idx,
				"date_from": formatdate(day_from, "MMMM dd, yyyy") if day_from else "",
				"date_to": formatdate(day_to, "MMMM dd, yyyy") if day_to else "",
				"days": days,
				"inbound": inbound if inbound != "" else "",
				"outbound": outbound if outbound != "" else "",
				"balance": balance,
				"rate": storage_rate,
				"total": line_total,
				"remarks": remarks,
				"job": job.get("name"),
				"job_type": job_type,
			}
		)
	return rows


def _jobs_for_period(doc) -> List[Dict[str, Any]]:
	"""Warehouse Jobs (Putaway/Pick) overlapping the PB period for this customer.

	Prefer jobs already linked on Periodic Billing Charges; otherwise submitted
	jobs for the customer in date_from–date_to. When warehouse_contract is set,
	only jobs for that contract are included.
	"""
	if not doc.customer or not doc.date_from or not doc.date_to:
		return []

	linked: Set[str] = set()
	for row in doc.charges or []:
		if row.warehouse_job:
			linked.add(row.warehouse_job)

	filters: Dict[str, Any] = {
		"customer": doc.customer,
		"type": ["in", ["Putaway", "Pick"]],
		"job_open_date": ["between", [doc.date_from, doc.date_to]],
		"docstatus": ["<", 2],
	}
	if getattr(doc, "warehouse_contract", None):
		filters["warehouse_contract"] = doc.warehouse_contract

	# Prefer charge-linked jobs, but only those that match the PB contract filter above
	if linked:
		filters["name"] = ["in", list(linked)]
		jobs = frappe.get_all(
			"Warehouse Job",
			filters=filters,
			fields=["name", "type", "job_open_date", "total_handling_units", "warehouse_contract"],
			order_by="job_open_date asc, name asc",
		)
		# Stale charges may point at jobs from other contracts — fall back to period jobs
		if not jobs:
			filters.pop("name", None)
			filters["docstatus"] = 1
			jobs = frappe.get_all(
				"Warehouse Job",
				filters=filters,
				fields=["name", "type", "job_open_date", "total_handling_units", "warehouse_contract"],
				order_by="job_open_date asc, name asc",
			)
	else:
		filters["docstatus"] = 1
		jobs = frappe.get_all(
			"Warehouse Job",
			filters=filters,
			fields=["name", "type", "job_open_date", "total_handling_units", "warehouse_contract"],
			order_by="job_open_date asc, name asc",
		)

	# Qty: handling units moved on the job (not summed charge lines)
	out: List[Dict[str, Any]] = []
	for job in jobs:
		qty = flt(job.total_handling_units or 0)
		if not qty:
			qty = _distinct_hu_count(job.name)
		out.append(
			{
				"name": job.name,
				"type": job.type,
				"job_open_date": job.job_open_date,
				"qty": qty,
			}
		)
	return out


def _distinct_hu_count(job_name: str) -> float:
	rows = frappe.get_all(
		"Warehouse Job Item",
		filters={"parent": job_name, "handling_unit": ["is", "set"]},
		fields=["handling_unit"],
		distinct=True,
	)
	return flt(len(rows))


def _job_date_span(job: Dict[str, Any]):
	"""FROM/TO for a job: ops dates → WSL posting span → job_open_date."""
	name = job.get("name")
	open_date = getdate(job.get("job_open_date")) if job.get("job_open_date") else None

	# Warehouse Job Operations
	ops = frappe.db.sql(
		"""
		SELECT MIN(start_date) AS s, MAX(COALESCE(end_date, start_date)) AS e
		FROM `tabWarehouse Job Operations`
		WHERE parent=%s AND (start_date IS NOT NULL OR end_date IS NOT NULL)
		""",
		name,
		as_dict=True,
	)
	if ops and (ops[0].s or ops[0].e):
		day_from = getdate(ops[0].s or ops[0].e or open_date)
		day_to = getdate(ops[0].e or ops[0].s or open_date)
		return day_from, day_to

	# Stock ledger posting span
	wsl = frappe.db.sql(
		"""
		SELECT MIN(DATE(posting_date)) AS s, MAX(DATE(posting_date)) AS e
		FROM `tabWarehouse Stock Ledger`
		WHERE warehouse_job=%s AND posting_date IS NOT NULL
		""",
		name,
		as_dict=True,
	)
	if wsl and wsl[0].s:
		return getdate(wsl[0].s), getdate(wsl[0].e or wsl[0].s)

	return open_date, open_date


def _inclusive_days(day_from, day_to) -> int:
	if not day_from or not day_to:
		return 1
	delta = (getdate(day_to) - getdate(day_from)).days + 1
	return max(cint(delta), 1)


def _opening_balance(doc) -> float:
	"""Pallet/HU balance just before date_from (LAST MONTH BALANCE)."""
	if not doc.customer or not doc.date_from:
		return 0.0

	# Prefer first storage_details snapshot if populated
	if doc.storage_details:
		first_date = min(
			(getdate(r.date) for r in doc.storage_details if r.date),
			default=None,
		)
		if first_date and first_date <= getdate(doc.date_from):
			bal = sum(
				flt(r.hu_count or 0)
				for r in doc.storage_details
				if r.date and getdate(r.date) == first_date
			)
			return flt(bal)

	# Distinct HUs with positive stock for customer before period start
	try:
		rows = frappe.db.sql(
			"""
			SELECT COUNT(DISTINCT l.handling_unit) AS bal
			FROM `tabWarehouse Stock Ledger` l
			INNER JOIN `tabWarehouse Item` wi ON wi.name = l.item
			WHERE wi.customer = %s
			  AND l.handling_unit IS NOT NULL
			  AND DATE(l.posting_date) < %s
			  AND COALESCE(l.end_qty, 0) > 0
			  AND l.name IN (
				SELECT MAX(l2.name)
				FROM `tabWarehouse Stock Ledger` l2
				INNER JOIN `tabWarehouse Item` wi2 ON wi2.name = l2.item
				WHERE wi2.customer = %s
				  AND l2.handling_unit IS NOT NULL
				  AND DATE(l2.posting_date) < %s
				GROUP BY l2.handling_unit
			  )
			""",
			(doc.customer, doc.date_from, doc.customer, doc.date_from),
			as_dict=True,
		)
		if rows:
			return flt(rows[0].bal or 0)
	except Exception:
		frappe.log_error(title="Summary PB HTML opening balance")
	return 0.0


def _fallback_storage_rows(doc, storage_rate: float) -> List[Dict[str, Any]]:
	"""When no Putaway/Pick jobs: keep previous storage-charge fallback."""
	rows: List[Dict[str, Any]] = []
	no = 0
	for row in doc.charges or []:
		if (row.charge_type or "") == "Cost":
			continue
		if not _is_storage_charge(row):
			continue
		no += 1
		rows.append(
			{
				"no": no,
				"date_from": formatdate(doc.date_from, "MMMM dd, yyyy") if doc.date_from else "",
				"date_to": formatdate(doc.date_to, "MMMM dd, yyyy") if doc.date_to else "",
				"days": flt(row.quantity or 0),
				"inbound": "",
				"outbound": "",
				"balance": flt(row.quantity or 0),
				"rate": flt(row.unit_rate or storage_rate or 0),
				"total": flt(row.total or 0),
				"remarks": "",
			}
		)
	return rows


# ---------------------------------------------------------------------------
# Other charges
# ---------------------------------------------------------------------------


def _is_storage_charge(row) -> bool:
	if (row.charge_category or "") == "Storage":
		return True
	label = f"{row.item_name or ''} {row.item or ''}".upper()
	return "STORAGE" in label and "HANDLING" not in label


def _storage_rate(doc) -> float:
	rates: List[float] = []
	for row in doc.charges or []:
		if (row.charge_type or "") == "Cost":
			continue
		if _is_storage_charge(row) and row.unit_rate is not None:
			rates.append(flt(row.unit_rate))
	if rates:
		return rates[0]

	# Contract storage rate fallback
	if doc.warehouse_contract:
		rate = frappe.db.get_value(
			"Warehouse Contract Item",
			{"parent": doc.warehouse_contract, "storage_charge": 1},
			"rate",
		)
		if rate is not None:
			return flt(rate)
	return 0.0


def _build_other_charge_rows(doc, start_no: int = 1) -> List[Dict[str, Any]]:
	"""Aggregate non-storage charges by item (one HANDLING IN / OUT line, etc.)."""
	grouped: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
	for row in doc.charges or []:
		if (row.charge_type or "") == "Cost":
			continue
		if _is_storage_charge(row):
			continue
		if flt(row.total or 0) == 0 and flt(row.quantity or 0) == 0:
			continue

		item_key = row.item or _plain_text(row.item_name or "") or f"row-{row.idx}"
		label = (row.item_name or row.item or row.description or "CHARGE").strip()
		label = _plain_text(label).upper()
		qty = flt(row.quantity or 0)
		total = flt(row.total or 0)

		if item_key not in grouped:
			grouped[item_key] = {
				"description": label,
				"quantity": qty,
				"uom": row.uom or "",
				"total": total,
				"rates": [flt(row.unit_rate or 0)] if row.unit_rate is not None else [],
			}
		else:
			g = grouped[item_key]
			g["quantity"] = flt(g["quantity"] + qty)
			g["total"] = flt(g["total"] + total)
			if row.unit_rate is not None:
				g["rates"].append(flt(row.unit_rate))
			if not g["uom"] and row.uom:
				g["uom"] = row.uom

	rows: List[Dict[str, Any]] = []
	no = start_no
	for g in grouped.values():
		qty = flt(g["quantity"])
		total = flt(g["total"], 2)
		rates = g["rates"]
		if rates and len(set(flt(r, 6) for r in rates)) == 1:
			rate = flt(rates[0])
		elif qty:
			rate = flt(total / qty, 2)
		else:
			rate = 0.0
		rows.append(
			{
				"no": no,
				"description": g["description"],
				"quantity": qty,
				"uom": g["uom"],
				"rate": rate,
				"total": total,
				"remarks": "",
			}
		)
		no += 1
	return rows


def _period_label(date_from, date_to) -> str:
	if not date_from or not date_to:
		return ""
	df = getdate(date_from)
	dt = getdate(date_to)
	if df.year == dt.year and df.month == dt.month:
		return f"{formatdate(df, 'MMMM dd')}–{formatdate(dt, 'dd, yyyy')}".upper()
	return f"{formatdate(df, 'MMMM dd, yyyy')} – {formatdate(dt, 'MMMM dd, yyyy')}".upper()


def _plain_text(value: Optional[str]) -> str:
	if not value:
		return ""
	text = frappe.utils.strip_html(str(value))
	return " ".join(text.split())
