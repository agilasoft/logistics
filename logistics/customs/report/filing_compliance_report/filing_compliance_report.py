# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, date_diff, today


def execute(filters=None):
	"""Execute Filing Compliance Report"""
	filters = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "filing_type",
			"label": _("Filing Type"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "filing_number",
			"label": _("Filing Number"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "country",
			"label": _("Country"),
			"fieldtype": "Link",
			"options": "Country",
			"width": 120
		},
		{
			"fieldname": "eta",
			"label": _("ETA"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "submission_date",
			"label": _("Submission Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "days_to_eta",
			"label": _("Days to ETA"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "compliance_status",
			"label": _("Compliance Status"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 120
		}
	]


def get_data(filters):
	"""Get report data from all filing types"""
	data = []
	
	# Get US AMS filings
	ams_data = get_ams_data(filters)
	data.extend(ams_data)
	
	# Get CA eManifest filings
	emanifest_data = get_emanifest_data(filters)
	data.extend(emanifest_data)
	
	# Get JP AFR filings
	afr_data = get_afr_data(filters)
	data.extend(afr_data)
	
	# Get US ISF filings
	isf_data = get_isf_data(filters)
	data.extend(isf_data)
	
	# Sort by ETA
	data.sort(key=lambda x: x.get("eta") or today(), reverse=True)
	
	return data


def get_ams_data(filters):
	"""Get US AMS data"""
	conditions = get_ams_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			'US AMS' as filing_type,
			ams.ams_number as filing_number,
			'United States' as country,
			ams.estimated_arrival_date as eta,
			ams.submission_date,
			ams.status,
			ams.company
		FROM `tabUS AMS` ams
		WHERE ams.docstatus != 2
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate compliance status
	for row in data:
		row["days_to_eta"] = calculate_days_to_eta(row.get("eta"), row.get("submission_date"))
		row["compliance_status"] = get_compliance_status(row.get("status"), row.get("days_to_eta"))
	
	return data


def get_emanifest_data(filters):
	"""Get CA eManifest data"""
	conditions = get_emanifest_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			'CA eManifest' as filing_type,
			em.manifest_number as filing_number,
			'Canada' as country,
			em.eta,
			em.submission_date,
			em.status,
			em.company
		FROM `tabCA eManifest Forwarder` em
		WHERE em.docstatus != 2
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate compliance status
	for row in data:
		row["days_to_eta"] = calculate_days_to_eta(row.get("eta"), row.get("submission_date"))
		row["compliance_status"] = get_compliance_status(row.get("status"), row.get("days_to_eta"))
	
	return data


def get_afr_data(filters):
	"""Get JP AFR data"""
	conditions = get_afr_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			'JP AFR' as filing_type,
			afr.afr_number as filing_number,
			'Japan' as country,
			afr.eta,
			afr.submission_date,
			afr.status,
			afr.company
		FROM `tabJP AFR` afr
		WHERE afr.docstatus != 2
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate compliance status
	for row in data:
		row["days_to_eta"] = calculate_days_to_eta(row.get("eta"), row.get("submission_date"))
		row["compliance_status"] = get_compliance_status(row.get("status"), row.get("days_to_eta"))
	
	return data


def get_isf_data(filters):
	"""Get US ISF data"""
	conditions = get_isf_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			'US ISF' as filing_type,
			isf.isf_number as filing_number,
			'United States' as country,
			isf.estimated_arrival_date as eta,
			isf.submission_date,
			isf.status,
			isf.company
		FROM `tabUS ISF` isf
		WHERE isf.docstatus != 2
		{conditions}
	""".format(conditions=conditions), filters, as_dict=1)
	
	# Calculate compliance status
	for row in data:
		row["days_to_eta"] = calculate_days_to_eta(row.get("eta"), row.get("submission_date"))
		row["compliance_status"] = get_compliance_status(row.get("status"), row.get("days_to_eta"), is_isf=True)
	
	return data


def calculate_days_to_eta(eta, submission_date):
	"""Calculate days between submission and ETA"""
	if not eta or not submission_date:
		return None
	
	try:
		return date_diff(eta, submission_date)
	except Exception:
		return None


def get_compliance_status(status, days_to_eta, is_isf=False):
	"""Determine compliance status"""
	if status in ["Rejected", "Hold"]:
		return "Non-Compliant"
	
	if status == "Accepted":
		return "Compliant"
	
	if status == "Submitted":
		# For ISF, must be filed 24 hours before (at least 1 day)
		if is_isf:
			if days_to_eta and days_to_eta >= 1:
				return "Compliant"
			else:
				return "At Risk"
		else:
			if days_to_eta and days_to_eta >= 0:
				return "Compliant"
			else:
				return "At Risk"
	
	if status == "Draft":
		if days_to_eta and days_to_eta < 0:
			return "Overdue"
		elif days_to_eta and days_to_eta < 1:
			return "At Risk"
		else:
			return "Pending"
	
	return "Unknown"


def get_ams_conditions(filters):
	"""Build conditions for US AMS"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("ams.company = %(company)s")
	
	if filters.get("status"):
		conditions.append("ams.status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_emanifest_conditions(filters):
	"""Build conditions for CA eManifest"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("em.company = %(company)s")
	
	if filters.get("status"):
		conditions.append("em.status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_afr_conditions(filters):
	"""Build conditions for JP AFR"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("afr.company = %(company)s")
	
	if filters.get("status"):
		conditions.append("afr.status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_isf_conditions(filters):
	"""Build conditions for US ISF"""
	conditions = []
	
	if filters.get("company"):
		conditions.append("isf.company = %(company)s")
	
	if filters.get("status"):
		conditions.append("isf.status = %(status)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""

