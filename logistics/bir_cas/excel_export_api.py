# Copyright (c) 2026, Agilasoft and contributors

from __future__ import annotations

import frappe
from frappe.utils.file_manager import save_file

from logistics.bir_cas.company_info import resolve_company_from_filters
from logistics.bir_cas.excel_header import write_cas_workbook


@frappe.whitelist()
def export_cas_excel(
	report_title: str,
	row_matrix,
	period_label: str | None = None,
	company: str | None = None,
	filters=None,
	filename: str | None = None,
):
	"""Export a CAS report matrix to Excel with the standard BIR header block."""
	if isinstance(row_matrix, str):
		row_matrix = frappe.parse_json(row_matrix)
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	company = company or resolve_company_from_filters(filters)
	content = write_cas_workbook(
		row_matrix,
		company=company,
		report_title=report_title,
		period_label=period_label,
		filters=filters,
	)

	safe_title = (report_title or "CAS Report").replace("/", "-")
	file_name = filename or f"{safe_title}.xlsx"
	file_doc = save_file(file_name, content, None, None, is_private=0)
	return {"file_url": file_doc.file_url, "file_name": file_doc.file_name}
