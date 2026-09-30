# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Charge-summary rows for the Consol Job Profit HTML print format."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import frappe
from frappe.utils import flt, get_datetime, now_datetime

_MONEY = Decimal("0.01")
_AMOUNT_KEYS = ("revenue", "wip", "cost", "accrual")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_PROJECT_FIELDS = (
	"project_name",
	"company",
	"exhibit_type",
	"project_type",
	"show_open_date",
	"show_close_date",
)
_SHIPMENT_FIELDS = (
	"house",
	"exhibitor",
	"agent",
	"awb_bl",
	"opened",
	"closed",
)


def get_consol_job_profit_context(mice_project) -> dict[str, Any]:
	"""Return the full consol job profit page for one MICE Project."""
	project_name = _project_name(mice_project)
	if not project_name:
		return _empty_context()

	jobs = _load_jobs(project_name)
	entries_by_job = {
		job["job_number"]: _classified_entries(job["job_number"], job["company"])
		for job in jobs
	}
	report = build_consol_job_profit(jobs, entries_by_job, _charge_item_codes(project_name))
	dockets = _project_dockets(project_name)
	report["header"] = _build_header(mice_project, project_name, dockets)
	report["cargo"] = build_cargo_totals(dockets)
	return report


def format_consol_job_profit_amount(value) -> str:
	"""Thousands separators, two decimals, leading minus for negatives."""
	return "{:,.2f}".format(float(_money(value)))


def build_consol_job_profit(
	jobs: list[dict[str, Any]],
	entries_by_job: dict[str, list[dict[str, Any]]],
	extra_charge_codes: Any = None,
) -> dict[str, Any]:
	"""Group classified GL lines into charge-code rows and job blocks.

	Profit is revenue minus cost. WIP and accrual stay in their own columns.
	Disbursement amounts are left out. Both sections share the sum of the jobs.
	"""
	charge_buckets: dict[str, dict[str, Decimal]] = {}
	for code in extra_charge_codes or []:
		label = (code or "").strip()
		if label:
			charge_buckets.setdefault(label, _blank_amounts())

	job_rows: list[dict[str, Any]] = []
	totals = _blank_amounts()

	for job in jobs or []:
		job_number = (job.get("job_number") or "").strip()
		if not job_number:
			continue
		job_amounts = _blank_amounts()
		for entry in entries_by_job.get(job_number) or []:
			signed = _entry_amounts(entry)
			_add_amounts(job_amounts, signed)
			code = (entry.get("dimension_item") or "").strip()
			bucket = charge_buckets.setdefault(code, _blank_amounts())
			_add_amounts(bucket, signed)
		job_final = _finalize(job_amounts)
		_add_amounts(totals, job_final)
		job_rows.append(_job_row(job, job_number, job_final))

	charge_rows = [
		{"charge_code": code, **_as_floats(_finalize(amounts))}
		for code, amounts in charge_buckets.items()
	]
	charge_rows.sort(key=lambda row: (row["charge_code"] == "", (row["charge_code"] or "").lower()))
	final_totals = _as_floats(_finalize(totals))

	return {
		"charge_rows": charge_rows,
		"jobs": job_rows,
		"shipments": [_shipment_row(row) for row in job_rows],
		"totals": final_totals,
		"summary": build_consol_summary(final_totals),
	}


def _load_jobs(project_name: str) -> list[dict[str, Any]]:
	"""Dockets and MICE Jobs that can be matched to the General Ledger.

	A row needs a Job Number and Company. The same Job Number is listed once.
	"""
	raw: list[dict[str, Any]] = []
	for row in frappe.get_all(
		"Docket",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		fields=[
			"name",
			"job_number",
			"company",
			"exhibitor_name",
			"docket_date",
			"planned_end",
		],
		order_by="creation asc",
	):
		raw.append({**row, "doctype": "Docket", "linked_service": None, "opened_on": row.get("docket_date")})
	for row in frappe.get_all(
		"MICE Job",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		fields=[
			"name",
			"job_number",
			"company",
			"linked_service",
			"job_date",
			"planned_end",
		],
		order_by="creation asc",
	):
		raw.append({**row, "doctype": "MICE Job", "opened_on": row.get("job_date")})

	jobs: list[dict[str, Any]] = []
	seen: set[tuple[str, str]] = set()
	for row in raw:
		job_number = (row.get("job_number") or "").strip()
		company = (row.get("company") or "").strip()
		if not job_number or not company:
			continue
		key = (job_number, company)
		if key in seen:
			continue
		seen.add(key)
		parties = _shipment_parties(row.get("doctype"), row.get("name"), row.get("linked_service"))
		exhibitor = ""
		if row.get("doctype") == "Docket":
			exhibitor = (row.get("exhibitor_name") or "").strip()
		jobs.append(
			{
				"name": row.get("name"),
				"doctype": row.get("doctype"),
				"job_number": job_number,
				"company": company,
				"mode": _mode_code(row.get("doctype"), row.get("name"), row.get("linked_service")),
				"house": (row.get("name") or "").strip(),
				"exhibitor": exhibitor,
				"agent": parties["agent"],
				"awb_bl": parties["awb_bl"],
				"opened": format_consol_job_profit_date(row.get("opened_on")),
				"closed": format_consol_job_profit_date(row.get("planned_end")),
			}
		)
	jobs.sort(key=lambda job: job["job_number"])
	return jobs


def _shipment_parties(doctype: str | None, name: str | None, linked_service: str | None = None) -> dict[str, str]:
	"""Freight agent and house AWB or BL for one job."""
	services = _linked_service_rows(doctype, name, linked_service)
	agent = ""
	service_names: list[str] = []
	for service in services:
		service_name = (service.get("name") or "").strip()
		if service_name:
			service_names.append(service_name)
		if not agent:
			agent = (service.get("freight_agent") or service.get("freight_agent_sea") or "").strip()
	return {"agent": agent, "awb_bl": _house_document_number(service_names)}


def _linked_service_rows(doctype: str | None, name: str | None, linked_service: str | None = None) -> list[dict[str, Any]]:
	if not frappe.db.exists("DocType", "Linked Service"):
		return []
	rows: list[dict[str, Any]] = []
	owned: set[str] = set()
	if doctype and name:
		rows = frappe.get_all(
			"Linked Service",
			filters={"parent_booking_type": doctype, "parent_booking_name": name},
			fields=["name", "freight_agent", "freight_agent_sea"],
			order_by="creation asc",
		)
		owned = {(row.get("name") or "") for row in rows}
		extra = _extra_linked_service_names(doctype, name, owned)
	else:
		extra = []
	if linked_service and linked_service not in owned and linked_service not in extra:
		extra.append(linked_service)
	if extra:
		rows.extend(
			frappe.get_all(
				"Linked Service",
				filters={"name": ["in", extra]},
				fields=["name", "freight_agent", "freight_agent_sea"],
				order_by="creation asc",
			)
		)
	return rows


def _extra_linked_service_names(doctype: str, name: str, owned: set[str]) -> list[str]:
	if not frappe.db.exists("DocType", "Linked Service Usage"):
		return []
	try:
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		return [svc for svc in get_linked_services_used_by(doctype, name) if svc and svc not in owned]
	except Exception:
		return []


def _house_document_number(service_names: list[str]) -> str:
	"""First house AWB, then house BL, on the freight document for these services."""
	names = [name for name in service_names if name]
	if not names:
		return ""
	if frappe.db.exists("DocType", "Air Shipment"):
		for row in frappe.get_all(
			"Air Shipment",
			filters={"linked_service": ["in", names]},
			fields=["house_awb_no", "house_awb"],
			order_by="creation asc",
		):
			number = (row.get("house_awb_no") or row.get("house_awb") or "").strip()
			if number:
				return number
	if frappe.db.exists("DocType", "Sea Shipment"):
		for row in frappe.get_all(
			"Sea Shipment",
			filters={"linked_service": ["in", names]},
			fields=["house_bl"],
			order_by="creation asc",
		):
			number = (row.get("house_bl") or "").strip()
			if number:
				return number
	return ""


def _mode_code(doctype: str | None, name: str | None, linked_service: str | None = None) -> str:
	"""Load Type on the job's linked service, or UNA when none is set."""
	codes = list(_load_type_codes(doctype, name))
	if linked_service and not any((code or "").strip() for code in codes):
		try:
			codes.append(frappe.db.get_value("Linked Service", linked_service, "load_type"))
		except Exception:
			pass
	return _mode_from_load_types(codes)


def _mode_from_load_types(load_types) -> str:
	for load_type in load_types or []:
		code = (load_type or "").strip()
		if code:
			return code
	return "UNA"


def _load_type_codes(doctype: str | None, name: str | None) -> list[str]:
	if not doctype or not name:
		return []
	if not frappe.db.exists("DocType", "Linked Service"):
		return []
	rows = frappe.get_all(
		"Linked Service",
		filters={"parent_booking_type": doctype, "parent_booking_name": name},
		fields=["name", "load_type"],
		order_by="creation asc",
	)
	codes = [(row.get("load_type") or "") for row in rows]
	if not frappe.db.exists("DocType", "Linked Service Usage"):
		return codes
	try:
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		owned = {row.get("name") for row in rows}
		extra = [svc for svc in get_linked_services_used_by(doctype, name) if svc and svc not in owned]
	except Exception:
		return codes
	if not extra:
		return codes
	more = frappe.get_all(
		"Linked Service",
		filters={"name": ["in", extra]},
		fields=["load_type"],
		order_by="creation asc",
	)
	codes.extend((row.get("load_type") or "") for row in more)
	return codes


def _classified_entries(job_number: str, company: str) -> list[dict[str, Any]]:
	from logistics.job_management.api import _get_job_gl_entries_classified

	return (
		_get_job_gl_entries_classified(
			job_number=job_number,
			company=company,
			max_fetch=100000,
		)
		or []
	)


def _charge_item_codes(project_name: str) -> set[str]:
	"""Item codes on the project and its jobs, including codes with no GL yet."""
	codes: set[str] = set()
	_collect_item_codes(
		codes,
		"MICE Project Consolidation Charges",
		{"parent": project_name, "parenttype": "MICE Project"},
	)
	docket_names = frappe.get_all(
		"Docket",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		pluck="name",
	)
	if docket_names:
		_collect_item_codes(
			codes,
			"MICE Project Charges",
			{"parent": ["in", docket_names], "parenttype": "Docket"},
		)
	mice_job_names = frappe.get_all(
		"MICE Job",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		pluck="name",
	)
	if mice_job_names:
		_collect_item_codes(
			codes,
			"Transport Job Charges",
			{"parent": ["in", mice_job_names], "parenttype": "MICE Job"},
		)
	return codes


def _collect_item_codes(codes: set[str], doctype: str, filters: dict) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	for row in frappe.get_all(doctype, filters=filters, fields=["item_code"]):
		item_code = (row.get("item_code") or "").strip()
		if item_code:
			codes.add(item_code)


def _entry_amounts(entry: dict[str, Any]) -> dict[str, Decimal]:
	return {
		"revenue": _money(entry.get("revenue_amount")),
		"wip": _money(entry.get("wip_amount")),
		"cost": _money(entry.get("cost_amount")),
		"accrual": _money(entry.get("accrual_amount")),
	}


def _blank_amounts() -> dict[str, Decimal]:
	return {key: Decimal("0.00") for key in _AMOUNT_KEYS}


def _add_amounts(target: dict[str, Decimal], source: dict[str, Decimal]) -> None:
	for key in _AMOUNT_KEYS:
		target[key] = target[key] + source[key]


def _finalize(amounts: dict[str, Decimal]) -> dict[str, Decimal]:
	final = {key: _money(amounts.get(key)) for key in _AMOUNT_KEYS}
	final["profit"] = _money(final["revenue"] - final["cost"])
	return final


def _as_floats(amounts: dict[str, Decimal]) -> dict[str, float]:
	return {key: float(amounts[key]) for key in (*_AMOUNT_KEYS, "profit")}


def _money(value) -> Decimal:
	return Decimal(str(flt(value or 0))).quantize(_MONEY, rounding=ROUND_HALF_UP)


def _job_row(job: dict[str, Any], job_number: str, amounts: dict[str, Decimal]) -> dict[str, Any]:
	row = {
		"job_number": job_number,
		"mode": (job.get("mode") or "").strip() or "UNA",
		**_as_floats(amounts),
	}
	for field in _SHIPMENT_FIELDS:
		row[field] = (job.get(field) or "").strip() if isinstance(job.get(field), str) else (job.get(field) or "")
	if not row.get("house"):
		row["house"] = (job.get("name") or "").strip()
	return row


def _shipment_row(job_row: dict[str, Any]) -> dict[str, str]:
	return {field: job_row.get(field) or "" for field in ("job_number", "mode", *_SHIPMENT_FIELDS)}


def build_consol_summary(totals: dict[str, Any]) -> dict[str, Any]:
	"""Header figures. Income adds WIP. Expense adds accrual. Line profit does not."""
	revenue = _money(totals.get("revenue"))
	wip = _money(totals.get("wip"))
	cost = _money(totals.get("cost"))
	accrual = _money(totals.get("accrual"))
	income = _money(revenue + wip)
	expense = _money(cost + accrual)
	rev_cst = _money(revenue - cost)
	wip_acr = _money(wip - accrual)
	profit = _money(income - expense)
	return {
		"revenue": float(revenue),
		"wip": float(wip),
		"cost": float(cost),
		"accrual": float(accrual),
		"income": float(income),
		"expense": float(expense),
		"rev_cst": float(rev_cst),
		"wip_acr": float(wip_acr),
		"profit": float(profit),
		"profit_cost_pct": _percent(profit, cost),
		"profit_rev_pct": _percent(profit, revenue),
	}


def build_cargo_totals(rows: list[dict[str, Any]] | None) -> dict[str, str]:
	"""Sum Docket packing totals for the consol summary cargo line."""
	containers = Decimal("0")
	teus = Decimal("0")
	weight = Decimal("0")
	volume = Decimal("0")
	chargeable = Decimal("0")
	packages = Decimal("0")
	weight_uom = ""
	volume_uom = ""
	chargeable_uom = ""
	for row in rows or []:
		containers += Decimal(str(flt(row.get("total_containers"))))
		teus += Decimal(str(flt(row.get("total_teus"))))
		weight += Decimal(str(flt(row.get("total_weight"))))
		volume += Decimal(str(flt(row.get("total_volume"))))
		chargeable += Decimal(str(flt(row.get("chargeable"))))
		packages += Decimal(str(flt(row.get("total_packages"))))
		weight_uom = weight_uom or (row.get("total_weight_uom") or "").strip()
		volume_uom = volume_uom or (row.get("total_volume_uom") or "").strip()
		chargeable_uom = chargeable_uom or (row.get("chargeable_weight_uom") or "").strip()
	return {
		"containers": _format_count(containers),
		"teu": _format_count(teus),
		"weight": _format_measure(weight, weight_uom),
		"volume": _format_measure(volume, volume_uom),
		"chargeable": _format_measure(chargeable, chargeable_uom),
		"packages": f"{_format_count(packages)} Package(s)",
	}


def build_routing(project: dict[str, Any], services: list[dict[str, Any]], dockets: list[dict[str, Any]]) -> dict[str, str]:
	"""First load port, last discharge port, carrier, and ETD/ETA."""
	load_port = ""
	discharge_port = ""
	carrier = ""
	for service in services or []:
		if not load_port:
			load_port = (service.get("origin_port") or "").strip()
		if (service.get("destination_port") or "").strip():
			discharge_port = (service.get("destination_port") or "").strip()
		if not carrier:
			carrier = (service.get("shipping_line") or "").strip()
	etd = project.get("show_open_date") or _first_value(dockets, "planned_start")
	eta = project.get("show_close_date") or _last_value(dockets, "planned_end")
	return {
		"load_port": load_port,
		"discharge_port": discharge_port,
		"carrier": carrier,
		"etd": format_consol_job_profit_date(etd),
		"eta": format_consol_job_profit_date(eta),
	}


def employee_initials(employee_name: str | None) -> str:
	parts = [part for part in (employee_name or "").replace(",", " ").split() if part]
	letters = "".join(part[0] for part in parts if part[:1].isalpha())
	return letters[:3].upper()


def format_consol_job_profit_date(value, with_time: bool = False) -> str:
	if not value:
		return ""
	try:
		moment = get_datetime(value)
	except Exception:
		return ""
	text = f"{moment.day:02d}-{_MONTHS[moment.month - 1]}-{moment.year % 100:02d}"
	if with_time:
		text += f" {moment.hour:02d}:{moment.minute:02d}"
	return text


def _percent(part: Decimal, base: Decimal) -> str:
	if not base:
		return "0%"
	pct = (part / base * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
	return f"{int(pct)}%"


def _format_count(value: Decimal) -> str:
	number = value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
	text = format(number, "f").rstrip("0").rstrip(".")
	return text or "0"


def _format_measure(value: Decimal, uom: str) -> str:
	number = _format_count(value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
	label = (uom or "").strip()
	return f"{number} {label}".strip()


def _first_value(rows: list[dict[str, Any]], field: str):
	for row in rows or []:
		if row.get(field):
			return row.get(field)
	return None


def _last_value(rows: list[dict[str, Any]], field: str):
	found = None
	for row in rows or []:
		if row.get(field):
			found = row.get(field)
	return found


def _empty_header() -> dict[str, str]:
	return {
		"company_name": "",
		"title": "Consol Job Profit",
		"project_name": "",
		"consol": "",
		"page": "1 of 1",
		"printed": "",
		"master": "",
		"load_port": "",
		"discharge_port": "",
		"etd": "",
		"eta": "",
		"journey": "",
		"carrier": "",
		"payment_type": "",
		"consol_type": "",
		"sending_agent": "",
		"receiving_agent": "",
	}


def _build_header(mice_project, project_name: str, dockets: list[dict[str, Any]]) -> dict[str, str]:
	record = _project_record(mice_project, project_name)
	company = (record.get("company") or "").strip()
	company_name = _company_name(company)
	routing = build_routing(record, _linked_services_for_dockets([row.get("name") for row in dockets]), dockets)
	header = _empty_header()
	header.update(
		{
			"company_name": company_name,
			"project_name": (record.get("project_name") or "").strip(),
			"consol": project_name,
			"printed": format_consol_job_profit_date(now_datetime(), with_time=True),
			"master": (record.get("project_name") or "").strip(),
			"consol_type": (record.get("exhibit_type") or record.get("project_type") or "").strip(),
			"receiving_agent": company_name,
			**routing,
		}
	)
	return header


def _project_record(mice_project, project_name: str) -> dict[str, Any]:
	record: dict[str, Any] = {"name": project_name}
	source = None if isinstance(mice_project, str) else mice_project
	if source is not None:
		for field in _PROJECT_FIELDS:
			value = source.get(field) if isinstance(source, dict) else getattr(source, field, None)
			if value:
				record[field] = value
	missing = [field for field in _PROJECT_FIELDS if not record.get(field)]
	if missing and frappe.db.exists("MICE Project", project_name):
		db_row = frappe.db.get_value("MICE Project", project_name, missing, as_dict=True) or {}
		for field, value in db_row.items():
			if value and not record.get(field):
				record[field] = value
	return record


def _company_name(company: str) -> str:
	if not company:
		return ""
	try:
		return (frappe.db.get_value("Company", company, "company_name") or company).strip()
	except Exception:
		return company


def _project_dockets(project_name: str) -> list[dict[str, Any]]:
	return frappe.get_all(
		"Docket",
		filters={"exhibit": project_name, "docstatus": ["<", 2]},
		fields=[
			"name",
			"planned_start",
			"planned_end",
			"total_containers",
			"total_teus",
			"total_packages",
			"total_weight",
			"total_weight_uom",
			"total_volume",
			"total_volume_uom",
			"chargeable",
			"chargeable_weight_uom",
		],
		order_by="creation asc",
	)


def _linked_services_for_dockets(docket_names: list[str]) -> list[dict[str, Any]]:
	names = [name for name in docket_names if name]
	if not names or not frappe.db.exists("DocType", "Linked Service"):
		return []
	return frappe.get_all(
		"Linked Service",
		filters={"parent_booking_type": "Docket", "parent_booking_name": ["in", names]},
		fields=["origin_port", "destination_port", "shipping_line"],
		order_by="creation asc",
	)


def _empty_context() -> dict[str, Any]:
	totals = _as_floats(_finalize(_blank_amounts()))
	return {
		"charge_rows": [],
		"jobs": [],
		"shipments": [],
		"totals": totals,
		"summary": build_consol_summary(totals),
		"header": _empty_header(),
		"cargo": build_cargo_totals([]),
	}


def _project_name(mice_project) -> str:
	if isinstance(mice_project, str):
		return mice_project.strip()
	if mice_project is None:
		return ""
	if isinstance(mice_project, dict):
		return (mice_project.get("name") or "").strip()
	return (getattr(mice_project, "name", None) or "").strip()
