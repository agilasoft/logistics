# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Opportunity service scopes: totals and YTD virtual profitability from customer GL."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import flt, getdate, today

JOB_TYPES_BY_OPPORTUNITY_SERVICE_TYPE: dict[str, tuple[str, ...]] = {
	"Air": ("Air Shipment", "Air Booking"),
	"Sea": ("Sea Shipment", "Sea Booking"),
	"Transport": ("Transport Job", "Transport Order"),
	"Customs": ("Declaration", "Declaration Order"),
	"Warehousing": (
		"Warehouse Job",
		"Inbound Order",
		"Release Order",
		"Transfer Order",
		"Cross-Docking Order",
	),
	"Time Sensitive": ("Time Sensitive Case",),
	"Special Project": ("Special Project", "Project Job", "Project Order"),
	"MICE": ("Docket", "MICE Project", "MICE Job", "MICE Order", "Exhibit Job", "Exhibit Order"),
}


def populate_virtual_scope_actuals(doc: Any) -> dict:
	"""Refresh scope totals from virtual row properties (not persisted)."""
	scopes = getattr(doc, "custom_opportunity_scopes", None) or []
	if not scopes:
		_clear_scope_totals(doc)
		return _scope_actuals_payload(doc)

	_update_scope_totals(doc)
	return _scope_actuals_payload(doc)


def populate_virtual_scope_actuals_for_rows(
	scope_rows: list[dict] | list[Any],
	company: str | None,
	customer: str | None = None,
) -> list[dict]:
	"""Compute virtual YTD actuals for scope dicts (used before Opportunity is saved)."""
	results = []
	for row in scope_rows or []:
		row_data = row if isinstance(row, dict) else row.as_dict()
		service_type = (row_data.get("service_type") or row_data.get("main_service") or "").strip()
		profit = get_customer_service_ytd_profitability(customer, company, service_type)
		results.append(
			{
				"name": row_data.get("name"),
				"idx": row_data.get("idx"),
				"actual_revenue": profit.get("revenue") or 0,
				"actual_profit": profit.get("gross_profit") or 0,
			}
		)
	return results


def get_customer_service_ytd_profitability(
	customer: str | None,
	company: str | None,
	service_type: str | None = None,
) -> dict[str, float]:
	"""YTD GL revenue and gross profit for a customer, optionally scoped by service type."""
	customer = (customer or "").strip()
	company = (company or "").strip()
	if not customer or not company:
		return {"revenue": 0.0, "gross_profit": 0.0}

	try:
		from logistics.job_management.job_360 import (
			_bulk_gl_rollup,
			_fetch_source_docs,
			_operational_row,
		)
	except Exception:
		return {"revenue": 0.0, "gross_profit": 0.0}

	service_type = (service_type or "").strip()
	job_types = list(JOB_TYPES_BY_OPPORTUNITY_SERVICE_TYPE.get(service_type, ()))
	if service_type and not job_types:
		return {"revenue": 0.0, "gross_profit": 0.0}

	filters: dict[str, Any] = {"company": company}
	try:
		from erpnext.accounts.utils import get_fiscal_year

		fy = get_fiscal_year(today(), company=company, raise_on_missing=False)
		if fy:
			filters["from_date"] = fy[1]
			filters["to_date"] = today()
	except Exception:
		today_date = getdate(today())
		filters["from_date"] = today_date.replace(month=1, day=1)
		filters["to_date"] = today_date

	jn_filters: dict[str, Any] = {"company": company, "docstatus": ["<", 2]}
	if job_types:
		jn_filters["job_type"] = ["in", job_types]

	jn_rows = frappe.get_all(
		"Job Number",
		filters=jn_filters,
		fields=["name", "job_type", "job_no"],
		limit_page_length=0,
	)
	if not jn_rows:
		return {"revenue": 0.0, "gross_profit": 0.0}

	by_type: dict[str, list[str]] = defaultdict(list)
	for row in jn_rows:
		if row.get("job_type") and row.get("job_no"):
			by_type[row["job_type"]].append(row["job_no"])

	source_doc_index: dict[str, dict[str, Any]] = {}
	for job_type, names in by_type.items():
		source_doc_index[job_type] = _fetch_source_docs(job_type, names)

	matching_job_numbers: list[str] = []
	for row in jn_rows:
		job_type = row.get("job_type") or ""
		job_no = row.get("job_no") or ""
		source_doc = (source_doc_index.get(job_type) or {}).get(job_no) or {}
		ops = _operational_row(job_type, source_doc)
		if (ops.get("customer") or "").strip() != customer:
			continue
		matching_job_numbers.append(row["name"])

	if not matching_job_numbers:
		return {"revenue": 0.0, "gross_profit": 0.0}

	try:
		gl_index = _bulk_gl_rollup(filters=filters, job_names=matching_job_numbers)
	except Exception:
		frappe.log_error(title="Opportunity scope YTD profitability", message=frappe.get_traceback())
		return {"revenue": 0.0, "gross_profit": 0.0}

	revenue = sum(flt(entry.get("revenue")) for entry in gl_index.values())
	gross_profit = sum(flt(entry.get("gross_profit")) for entry in gl_index.values())
	return {"revenue": revenue, "gross_profit": gross_profit}


def get_scope_ytd_profitability(scope_row: Any, opportunity_doc: Any | None = None) -> dict[str, float]:
	"""YTD profitability for one scope row from its parent Opportunity customer."""
	customer = resolve_opportunity_customer(opportunity_doc, scope_row)
	company = resolve_opportunity_company(opportunity_doc, scope_row)
	if isinstance(scope_row, dict):
		service_type = (scope_row.get("service_type") or scope_row.get("main_service") or "").strip()
	else:
		service_type = (scope_row.get("service_type") or scope_row.get("main_service") or "").strip()
	return get_customer_service_ytd_profitability(customer, company, service_type)


def resolve_opportunity_customer(opportunity_doc: Any | None, scope_row: Any | None = None) -> str | None:
	if opportunity_doc:
		if (getattr(opportunity_doc, "opportunity_from", None) or "").strip() == "Customer":
			party = (getattr(opportunity_doc, "party_name", None) or "").strip()
			if party:
				return party
		return None

	parenttype = None
	parent = None
	if scope_row is not None:
		if isinstance(scope_row, dict):
			parenttype = scope_row.get("parenttype")
			parent = scope_row.get("parent")
		else:
			parenttype = scope_row.get("parenttype")
			parent = scope_row.get("parent")

	if parenttype == "Opportunity" and parent and not str(parent).startswith("new-"):
		try:
			opp = frappe.get_doc("Opportunity", parent)
		except frappe.DoesNotExistError:
			return None
		return resolve_opportunity_customer(opp)

	return None


def resolve_opportunity_company(opportunity_doc: Any | None, scope_row: Any | None = None) -> str | None:
	if opportunity_doc:
		company = (getattr(opportunity_doc, "company", None) or "").strip()
		return company or None

	parenttype = None
	parent = None
	if scope_row is not None:
		if isinstance(scope_row, dict):
			parenttype = scope_row.get("parenttype")
			parent = scope_row.get("parent")
		else:
			parenttype = scope_row.get("parenttype")
			parent = scope_row.get("parent")

	if parenttype == "Opportunity" and parent and not str(parent).startswith("new-"):
		return frappe.db.get_value("Opportunity", parent, "company")

	return None


def _update_scope_totals(doc: Any) -> None:
	scopes = getattr(doc, "custom_opportunity_scopes", None) or []
	total_value = sum(flt(row.opportunity_value) for row in scopes)
	total_revenue = sum(flt(getattr(row, "actual_revenue", 0)) for row in scopes)
	total_profit = sum(flt(getattr(row, "actual_profit", 0)) for row in scopes)

	doc.custom_total_scope_opportunity_value = total_value
	doc.custom_total_scope_actual_revenue = total_revenue
	doc.custom_total_scope_actual_profit = total_profit

	if scopes and total_value:
		doc.opportunity_amount = total_value
		conversion_rate = flt(doc.conversion_rate) or 1.0
		doc.base_opportunity_amount = flt(total_value) * conversion_rate


def _clear_scope_totals(doc: Any) -> None:
	doc.custom_total_scope_opportunity_value = 0
	doc.custom_total_scope_actual_revenue = 0
	doc.custom_total_scope_actual_profit = 0


def _scope_actuals_payload(doc: Any) -> dict:
	return {
		"custom_total_scope_opportunity_value": flt(doc.custom_total_scope_opportunity_value),
		"custom_total_scope_actual_revenue": flt(doc.custom_total_scope_actual_revenue),
		"custom_total_scope_actual_profit": flt(doc.custom_total_scope_actual_profit),
		"opportunity_amount": flt(doc.opportunity_amount),
		"scopes": [
			{
				"name": row.name,
				"idx": row.idx,
				"actual_revenue": flt(getattr(row, "actual_revenue", 0)),
				"actual_profit": flt(getattr(row, "actual_profit", 0)),
			}
			for row in (getattr(doc, "custom_opportunity_scopes", None) or [])
		],
	}


def on_opportunity_validate(doc: Any, method: str | None = None) -> None:
	if not frappe.get_meta("Opportunity").has_field("custom_opportunity_scopes"):
		return
	populate_virtual_scope_actuals(doc)


def on_opportunity_onload(doc: Any, method: str | None = None) -> None:
	if not frappe.get_meta("Opportunity").has_field("custom_opportunity_scopes"):
		return
	populate_virtual_scope_actuals(doc)
