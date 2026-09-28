# Copyright (c) 2026, Agilasoft and contributors

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.query_report import _export_query, export_query as _frappe_export_query
from frappe.desk.utils import pop_csv_params, provide_binary_file
from frappe.desk.query_report import clean_params, parse_json

from logistics.bir_cas.company_info import resolve_company_from_filters
from logistics.bir_cas.excel_header import ensure_bir_cas_excel_header
from logistics.bir_cas.report_utils import is_bir_cas_report, period_label_from_filters


@frappe.whitelist()
def export_query():
	"""Wrap Frappe query report export to inject BIR CAS header rows for Excel."""
	form_params = frappe._dict(frappe.local.form_dict)
	csv_params = pop_csv_params(form_params)
	clean_params(form_params)
	parse_json(form_params)

	report_name = form_params.get("report_name")
	file_format = form_params.get("file_format_type")
	use_cas_header = file_format == "Excel" and is_bir_cas_report(report_name)

	if not use_cas_header:
		return _frappe_export_query()

	export_in_background = int(form_params.export_in_background or 0)
	if export_in_background:
		user = frappe.session.user
		user_email = frappe.get_cached_value("User", user, "email")
		frappe.enqueue(
			"logistics.bir_cas.export_query.run_export_query_job",
			user_email=user_email,
			form_params=form_params,
			csv_params=csv_params,
			queue="long",
			now=frappe.flags.in_test,
		)
		frappe.msgprint(
			frappe._(
				"Your report is being generated in the background. You will receive an email on {0} with a download link once it is ready."
			).format(user_email)
		)
		return

	return _export_with_cas_header(form_params, csv_params)


def run_export_query_job(user_email: str, form_params, csv_params):
	from frappe.desk.utils import send_report_email

	report_name, file_extension, content = _export_with_cas_header(
		form_params, csv_params, populate_response=False
	)
	send_report_email(
		user_email, report_name, file_extension, content, attached_to_name=form_params.report_name
	)


def _export_with_cas_header(form_params, csv_params, populate_response=True):
	report_name, file_extension, content = _export_query(form_params, csv_params, populate_response=False)

	if file_extension != "xlsx":
		if populate_response:
			provide_binary_file(_(report_name), file_extension, content)
			return
		return report_name, file_extension, content

	filters = form_params.filters
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)

	company = resolve_company_from_filters(filters)
	period_label = period_label_from_filters(filters)
	display_name = frappe.get_cached_value("Report", form_params.report_name, "report_name") or report_name

	content = ensure_bir_cas_excel_header(
		content,
		company=company,
		report_title=display_name,
		period_label=period_label,
		filters=filters,
	)

	if not populate_response:
		return report_name, file_extension, content

	provide_binary_file(_(report_name), file_extension, content)
