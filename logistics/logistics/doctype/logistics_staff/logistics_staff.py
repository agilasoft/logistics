# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Logistics Staff: role list for sales, operations, customer service, and warehouse.

Operational documents link here instead of Employee so Employee user permissions
do not restrict who can be selected.
"""

import frappe
from frappe import _
from frappe.model.document import Document

DOCTYPE = "Logistics Staff"

ROLE_FIELDS = (
	"sales_rep",
	"operations_rep",
	"customer_service_rep",
	"warehouseman",
)

# Employee custom checkboxes copied onto Logistics Staff.
EMPLOYEE_ROLE_COLUMNS = {
	"custom_sales_rep": "sales_rep",
	"custom_operations_rep": "operations_rep",
	"custom_customer_service_rep": "customer_service_rep",
	"custom_warehouseman": "warehouseman",
}

# DocType field -> Logistics Staff role. Values already stored are Employee names.
STAFF_LINK_SOURCES = (
	(
		"Sales Quote",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Sales Quote Pack",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Change Request",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Air Booking",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Air Shipment",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Sea Booking",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Sea Shipment",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Transport Order",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Transport Job",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Declaration",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Declaration Order",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Special Project",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Project Job",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Exhibit Job",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"Docket",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"MICE Project",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"MICE Job",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	(
		"MICE Order",
		{
			"sales_rep": "sales_rep",
			"operations_rep": "operations_rep",
			"customer_service_rep": "customer_service_rep",
		},
	),
	("Warehouse Job Operations", {"employee": "warehouseman"}),
)


def staff_link_filters(role_field):
	"""Link-field filter: active Logistics Staff with this role."""
	return [
		[DOCTYPE, role_field, "=", 1],
		[DOCTYPE, "is_active", "=", 1],
	]


class LogisticsStaff(Document):
	def validate(self):
		if not any(self.get(field) for field in ROLE_FIELDS):
			frappe.throw(
				_(
					"Select at least one role: Sales Rep, Operations Rep, Customer Service Rep, or Warehouseman."
				)
			)
		self._pull_employee_details()

	def _pull_employee_details(self):
		"""Copy display fields with a direct read so Employee permissions do not blank them."""
		if not self.employee or not frappe.db.exists("Employee", self.employee):
			return
		details = frappe.db.get_value(
			"Employee",
			self.employee,
			["employee_name", "company", "status", "user_id"],
			as_dict=True,
		)
		if not details:
			return
		self.employee_name = details.employee_name
		self.company = details.company
		self.status = details.status
		self.user_id = details.user_id


def ensure_logistics_staff(
	employee,
	sales_rep=1,
	operations_rep=1,
	customer_service_rep=1,
	warehouseman=0,
	is_active=1,
):
	"""Return the Logistics Staff name for an Employee, creating or updating roles.

	The document name matches the Employee name, so existing link values stay valid.
	Role flags already set are left on. Pass 1 to turn a role on.
	"""
	if not employee or not frappe.db.exists("Employee", employee):
		return None
	if not frappe.db.table_exists("Logistics Staff"):
		return None

	wanted = {
		"sales_rep": 1 if sales_rep else 0,
		"operations_rep": 1 if operations_rep else 0,
		"customer_service_rep": 1 if customer_service_rep else 0,
		"warehouseman": 1 if warehouseman else 0,
	}
	if not any(wanted.values()):
		return frappe.db.get_value(DOCTYPE, {"employee": employee}, "name")

	return _upsert_staff(employee, wanted, activate=bool(is_active))


def sync_logistics_staff_from_employee(doc, method=None):
	"""Turn on Logistics Staff roles that are checked on Employee. Does not clear roles."""
	if not doc or not doc.name or not frappe.db.table_exists("Logistics Staff"):
		return
	wanted = {}
	for column, role in EMPLOYEE_ROLE_COLUMNS.items():
		if doc.get(column):
			wanted[role] = 1
	if not wanted:
		return
	_upsert_staff(doc.name, wanted, activate=doc.get("status") != "Left")


def seed_logistics_staff_from_employees_and_links():
	"""Create Logistics Staff for flagged employees and employees already used on documents."""
	if not frappe.db.table_exists("Logistics Staff") or not frappe.db.table_exists("Employee"):
		return 0

	roles_by_employee = {}

	employee_columns = [
		column
		for column in EMPLOYEE_ROLE_COLUMNS
		if frappe.db.has_column("Employee", column)
	]
	if employee_columns:
		or_filters = {column: 1 for column in employee_columns}
		for row in frappe.get_all(
			"Employee",
			or_filters=or_filters,
			fields=["name", *employee_columns],
			limit_page_length=0,
		):
			flags = roles_by_employee.setdefault(row.name, {})
			for column, role in EMPLOYEE_ROLE_COLUMNS.items():
				if row.get(column):
					flags[role] = 1

	for doctype, field_map in STAFF_LINK_SOURCES:
		if not frappe.db.table_exists(doctype):
			continue
		for fieldname, role in field_map.items():
			if not frappe.db.has_column(doctype, fieldname):
				continue
			for value in frappe.get_all(
				doctype,
				filters={fieldname: ["is", "set"]},
				pluck=fieldname,
				distinct=True,
				limit_page_length=0,
			):
				if not value or not frappe.db.exists("Employee", value):
					continue
				roles_by_employee.setdefault(value, {})[role] = 1

	created_or_updated = 0
	for employee, flags in roles_by_employee.items():
		if not flags:
			continue
		status = frappe.db.get_value("Employee", employee, "status")
		if _upsert_staff(employee, flags, activate=status != "Left"):
			created_or_updated += 1
	return created_or_updated


def _upsert_staff(employee, flags, activate=True):
	"""Insert or add role flags. ``flags`` values of 1 turn a role on."""
	existing = frappe.db.get_value(DOCTYPE, {"employee": employee}, "name")
	if existing:
		current = frappe.db.get_value(DOCTYPE, existing, list(ROLE_FIELDS), as_dict=True) or {}
		updates = {}
		for role, enabled in flags.items():
			if enabled and not current.get(role):
				updates[role] = 1
		if updates:
			frappe.db.set_value(DOCTYPE, existing, updates, update_modified=False)
		return existing

	doc = frappe.new_doc(DOCTYPE)
	doc.employee = employee
	doc.is_active = 1 if activate else 0
	for role in ROLE_FIELDS:
		doc.set(role, 1 if flags.get(role) else 0)
	doc.insert(ignore_permissions=True)
	return doc.name
