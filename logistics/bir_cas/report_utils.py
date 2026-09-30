# Copyright (c) 2026, Agilasoft and contributors

from __future__ import annotations

import frappe
from frappe.utils import formatdate, getdate


def is_bir_cas_report(report_name: str | None) -> bool:
	if not report_name:
		return False

	from logistics.bir_cas.constants import BIR_CAS_EXCEL_REPORT_NAMES

	if report_name in BIR_CAS_EXCEL_REPORT_NAMES:
		return True

	meta = frappe.get_cached_value("Report", report_name, ["module", "report_name"], as_dict=True)
	if not meta:
		return False

	module = (meta.module or "").strip().lower()
	if module in {"bir cas", "cas", "bir_cas"} or "cas" in module:
		return True

	title = (meta.report_name or report_name or "").lower()
	if "sales book" in title or title.startswith("bir "):
		return True

	return False


def period_label_from_filters(filters) -> str | None:
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, dict):
		return None

	from_date = filters.get("from_date") or filters.get("period_start_date")
	to_date = filters.get("to_date") or filters.get("period_end_date")
	if from_date and to_date:
		return f"{formatdate(getdate(from_date), 'MM-dd-yyyy')} TO {formatdate(getdate(to_date), 'MM-dd-yyyy')}"
	if from_date:
		return formatdate(getdate(from_date), "MM-dd-yyyy")
	return None


def _batch_date_stamp(value) -> str:
	"""Date-only filter shown as midnight, day/month/year, 12-hour clock."""
	day = getdate(value)
	return f"{day.day}/{day.month}/{day.year} 12:00:00 AM"


def cash_book_period_label_from_filters(filters) -> str | None:
	"""Cash Receipts Book batch range: Batch Date From:… Batch Date To:…"""
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, dict):
		return None

	from_date = filters.get("from_date") or filters.get("period_start_date")
	to_date = filters.get("to_date") or filters.get("period_end_date")
	if from_date and to_date:
		return (
			f"Batch Date From:{_batch_date_stamp(from_date)} "
			f"Batch Date To:{_batch_date_stamp(to_date)}"
		)
	if from_date:
		return f"Batch Date From:{_batch_date_stamp(from_date)}"
	return None


def _sales_book_date_stamp(value) -> str:
	"""Date-only filter shown as midnight, month/day/year, 12-hour clock."""
	day = getdate(value)
	return f"{day.month}/{day.day}/{day.year} 12:00:00 AM"


def sales_book_period_label_from_filters(filters) -> str | None:
	"""Sales Book range: Date From: … Date To: …"""
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, dict):
		return None

	from_date = filters.get("from_date") or filters.get("period_start_date")
	to_date = filters.get("to_date") or filters.get("period_end_date")
	if from_date and to_date:
		return (
			f"Date From: {_sales_book_date_stamp(from_date)} "
			f"Date To: {_sales_book_date_stamp(to_date)}"
		)
	if from_date:
		return f"Date From: {_sales_book_date_stamp(from_date)}"
	return None


def gl_period_label_from_filters(filters) -> str | None:
	"""CAS General Ledger period as YYYYMM to YYYYMM."""
	if not filters:
		return None
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	if not isinstance(filters, dict):
		return None

	from_date = filters.get("from_date") or filters.get("period_start_date")
	to_date = filters.get("to_date") or filters.get("period_end_date")
	if from_date and to_date:
		return f"{getdate(from_date).strftime('%Y%m')} to {getdate(to_date).strftime('%Y%m')}"
	if from_date:
		return getdate(from_date).strftime("%Y%m")
	return None
