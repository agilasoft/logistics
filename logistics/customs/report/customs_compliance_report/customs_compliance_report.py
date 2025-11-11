# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today, add_days, date_diff


def execute(filters=None):
	f = frappe._dict(filters or {})
	
	columns = get_columns()
	data = get_data(f)
	
	return columns, data


def get_columns():
	return [
		{"label": "Declaration", "fieldname": "declaration", "fieldtype": "Link", "options": "Declaration", "width": 150},
		{"label": "Date", "fieldname": "declaration_date", "fieldtype": "Date", "width": 100},
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Compliance Issue", "fieldname": "compliance_issue", "fieldtype": "Data", "width": 200},
		{"label": "Issue Type", "fieldname": "issue_type", "fieldtype": "Data", "width": 120},
		{"label": "Days Overdue", "fieldname": "days_overdue", "fieldtype": "Int", "width": 100},
		{"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 100}
	]


def get_data(filters):
	data = []
	
	# Get declarations with pending approvals
	if not filters.get("issue_type") or filters.get("issue_type") == "Pending Approval":
		pending_approvals = get_pending_approvals(filters)
		data.extend(pending_approvals)
	
	# Get declarations with missing documents
	if not filters.get("issue_type") or filters.get("issue_type") == "Missing Documents":
		missing_docs = get_missing_documents(filters)
		data.extend(missing_docs)
	
	# Get declarations with expired documents
	if not filters.get("issue_type") or filters.get("issue_type") == "Expired Documents":
		expired_docs = get_expired_documents(filters)
		data.extend(expired_docs)
	
	# Get overdue declarations (past SLA)
	if not filters.get("issue_type") or filters.get("issue_type") == "Overdue":
		overdue = get_overdue_declarations(filters)
		data.extend(overdue)
	
	# Sort by priority and days overdue
	data.sort(key=lambda x: (
		{"High": 0, "Medium": 1, "Low": 2}.get(x.get("priority", "Low"), 2),
		x.get("days_overdue", 0)
	))
	
	return data


def get_pending_approvals(filters):
	conditions = get_base_conditions(filters)
	conditions.append("d.status IN ('Draft', 'Submitted', 'In Progress')")
	
	declarations = frappe.db.sql("""
		SELECT
			d.name as declaration,
			d.declaration_date,
			d.customer,
			d.status,
			'Pending Approval' as compliance_issue,
			'Pending Approval' as issue_type,
			DATEDIFF(CURDATE(), d.declaration_date) as days_overdue,
			CASE
				WHEN DATEDIFF(CURDATE(), d.declaration_date) > 7 THEN 'High'
				WHEN DATEDIFF(CURDATE(), d.declaration_date) > 3 THEN 'Medium'
				ELSE 'Low'
			END as priority
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND {conditions}
	""".format(conditions=" AND ".join(conditions)), filters, as_dict=1)
	
	return declarations


def get_missing_documents(filters):
	conditions = get_base_conditions(filters)
	
	# Get declarations that require documents but don't have them
	declarations = frappe.db.sql("""
		SELECT DISTINCT
			d.name as declaration,
			d.declaration_date,
			d.customer,
			d.status,
			'Missing Required Documents' as compliance_issue,
			'Missing Documents' as issue_type,
			DATEDIFF(CURDATE(), d.declaration_date) as days_overdue,
			'Medium' as priority
		FROM `tabDeclaration` d
		LEFT JOIN `tabDeclaration Document` dd ON dd.parent = d.name AND dd.is_required = 1
		WHERE d.docstatus != 2
		AND {conditions}
		AND (dd.name IS NULL OR dd.attachment IS NULL OR dd.attachment = '')
	""".format(conditions=" AND ".join(conditions)), filters, as_dict=1)
	
	return declarations


def get_expired_documents(filters):
	conditions = get_base_conditions(filters)
	
	declarations = frappe.db.sql("""
		SELECT DISTINCT
			d.name as declaration,
			d.declaration_date,
			d.customer,
			d.status,
			CONCAT('Expired: ', dd.document_type) as compliance_issue,
			'Expired Documents' as issue_type,
			DATEDIFF(CURDATE(), dd.expiry_date) as days_overdue,
			CASE
				WHEN DATEDIFF(CURDATE(), dd.expiry_date) > 30 THEN 'High'
				WHEN DATEDIFF(CURDATE(), dd.expiry_date) > 7 THEN 'Medium'
				ELSE 'Low'
			END as priority
		FROM `tabDeclaration` d
		INNER JOIN `tabDeclaration Document` dd ON dd.parent = d.name
		WHERE d.docstatus != 2
		AND {conditions}
		AND dd.expiry_date IS NOT NULL
		AND dd.expiry_date < CURDATE()
	""".format(conditions=" AND ".join(conditions)), filters, as_dict=1)
	
	return declarations


def get_overdue_declarations(filters):
	conditions = get_base_conditions(filters)
	conditions.append("d.status NOT IN ('Approved', 'Rejected', 'Cancelled')")
	
	# Get declarations that are past their expected processing date
	# This is a simplified version - in production, you'd check against SLA from Customs Authority
	declarations = frappe.db.sql("""
		SELECT
			d.name as declaration,
			d.declaration_date,
			d.customer,
			d.status,
			'Past Expected Processing Date' as compliance_issue,
			'Overdue' as issue_type,
			DATEDIFF(CURDATE(), DATE_ADD(d.declaration_date, INTERVAL 5 DAY)) as days_overdue,
			CASE
				WHEN DATEDIFF(CURDATE(), DATE_ADD(d.declaration_date, INTERVAL 5 DAY)) > 10 THEN 'High'
				WHEN DATEDIFF(CURDATE(), DATE_ADD(d.declaration_date, INTERVAL 5 DAY)) > 5 THEN 'Medium'
				ELSE 'Low'
			END as priority
		FROM `tabDeclaration` d
		WHERE d.docstatus != 2
		AND {conditions}
		AND DATEDIFF(CURDATE(), DATE_ADD(d.declaration_date, INTERVAL 5 DAY)) > 0
	""".format(conditions=" AND ".join(conditions)), filters, as_dict=1)
	
	return declarations


def get_base_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("d.declaration_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("d.declaration_date <= %(to_date)s")
	
	if filters.get("customer"):
		conditions.append("d.customer = %(customer)s")
	
	if filters.get("company"):
		conditions.append("d.company = %(company)s")
	
	if filters.get("customs_authority"):
		conditions.append("d.customs_authority = %(customs_authority)s")
	
	return conditions if conditions else ["1=1"]


