# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests import IntegrationTestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate, random_string, today


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class TestExemptionCertificateDeclarationUsage(FrappeTestCase):
	"""Used Value / Used Quantity roll up from Related Declarations child rows."""

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_exemption_type(self):
		et_list = frappe.get_all("Exemption Type", pluck="name", filters={"is_active": 1}, limit=1)
		if et_list:
			return et_list[0]
		code = f"TEST-ET-{random_string(10)}"
		et = frappe.get_doc(
			{
				"doctype": "Exemption Type",
				"exemption_code": code,
				"exemption_name": "Test Exemption Type",
				"is_active": 1,
				"exemption_category": "Duty",
				"applicable_to": "Import",
			}
		)
		et.insert()
		return et.name

	def _company_customer_et(self):
		companies = frappe.get_all("Company", pluck="name", limit=1)
		if not companies:
			self.skipTest("No Company")
		customers = frappe.get_all("Customer", pluck="name", limit=1)
		if not customers:
			self.skipTest("No Customer")
		return companies[0], customers[0], self._ensure_exemption_type()

	def _new_cert_base(self, certificate_number, exemption_value=None, exemption_quantity=None):
		company, customer, et_name = self._company_customer_et()
		cert = frappe.new_doc("Exemption Certificate")
		cert.certificate_number = certificate_number
		cert.exemption_type = et_name
		cert.status = "Active"
		cert.issue_date = today()
		cert.issued_to_type = "Customer"
		cert.issued_to = customer
		cert.company = company
		cert.valid_from = getdate(nowdate())
		cert.valid_to = getdate(nowdate())
		if exemption_value is not None:
			cert.exemption_value = exemption_value
		if exemption_quantity is not None:
			cert.exemption_quantity = exemption_quantity
		return cert

	def test_used_value_and_remaining_aggregate_two_declarations(self):
		cn = f"EC-AGG-{random_string(10)}"
		cert = self._new_cert_base(cn, exemption_value=100000)
		cert.append("declarations", {"declaration": f"D-{cn}-A", "exempted_value": 40000})
		cert.append("declarations", {"declaration": f"D-{cn}-B", "exempted_value": 35000})
		cert.insert(ignore_links=True)
		cert.reload()
		self.assertEqual(cert.used_value, 75000)
		self.assertEqual(cert.remaining_value, 25000)

	def test_total_exempted_value_over_limit_raises(self):
		cn = f"EC-OVR-{random_string(10)}"
		cert = self._new_cert_base(cn, exemption_value=50000)
		cert.append("declarations", {"declaration": f"D-{cn}-A", "exempted_value": 30000})
		cert.append("declarations", {"declaration": f"D-{cn}-B", "exempted_value": 30000})
		with self.assertRaises(ValidationError):
			cert.insert(ignore_links=True)

	def test_duplicate_declaration_row_raises(self):
		cn = f"EC-DUP-{random_string(10)}"
		dname = f"D-{cn}-SAME"
		cert = self._new_cert_base(cn, exemption_value=100000)
		cert.append("declarations", {"declaration": dname, "exempted_value": 1000})
		cert.append("declarations", {"declaration": dname, "exempted_value": 2000})
		with self.assertRaises(ValidationError):
			cert.insert(ignore_links=True)

	def test_negative_exempted_value_raises(self):
		cn = f"EC-NEG-{random_string(10)}"
		cert = self._new_cert_base(cn, exemption_value=100000)
		cert.append("declarations", {"declaration": f"D-{cn}-A", "exempted_value": -1})
		with self.assertRaises(ValidationError):
			cert.insert(ignore_links=True)


class IntegrationTestExemptionCertificate(IntegrationTestCase):
	"""
	Integration tests for ExemptionCertificate.
	Use this class for testing interactions between multiple components.
	"""

	pass
