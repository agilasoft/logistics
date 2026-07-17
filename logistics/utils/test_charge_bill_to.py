# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.charge_bill_to import (
	get_default_bill_to,
	get_eligible_bill_to_customers,
	get_parent_customer,
)


class TestChargeBillTo(IntegrationTestCase):
	def test_get_parent_customer_prefers_local_customer(self):
		doc = frappe._dict(local_customer="LC-1", customer="C-1")
		self.assertEqual(get_parent_customer(doc), "LC-1")

	def test_get_parent_customer_falls_back_to_customer(self):
		doc = frappe._dict(customer="C-1")
		self.assertEqual(get_parent_customer(doc), "C-1")

	def test_get_default_bill_to_matches_parent_customer(self):
		doc = frappe._dict(local_customer="LC-1")
		self.assertEqual(get_default_bill_to(doc), "LC-1")

	def test_get_eligible_bill_to_customers_includes_party_and_agent_customers(self):
		parent_customer = "_Test Charge Bill To Parent"
		shipper_customer = "_Test Charge Bill To Shipper Cust"
		consignee_customer = "_Test Charge Bill To Consignee Cust"
		agent_customer = "_Test Charge Bill To Agent Cust"

		for name in (
			parent_customer,
			shipper_customer,
			consignee_customer,
			agent_customer,
		):
			if not frappe.db.exists("Customer", name):
				frappe.get_doc(
					{
						"doctype": "Customer",
						"customer_name": name,
						"customer_type": "Company",
					}
				).insert(ignore_permissions=True)

		shipper_code = "_T-CBT-SHIP"
		if not frappe.db.exists("Shipper", shipper_code):
			frappe.get_doc(
				{
					"doctype": "Shipper",
					"code": shipper_code,
					"shipper_name": shipper_code,
					"customer": shipper_customer,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Shipper", shipper_code, "customer", shipper_customer)

		consignee_code = "_T-CBT-CONS"
		if not frappe.db.exists("Consignee", consignee_code):
			frappe.get_doc(
				{
					"doctype": "Consignee",
					"code": consignee_code,
					"consignee_name": consignee_code,
					"customer": consignee_customer,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Consignee", consignee_code, "customer", consignee_customer)

		agent_code = "_T-CBT-AGENT"
		if not frappe.db.exists("Freight Agent", agent_code):
			frappe.get_doc(
				{
					"doctype": "Freight Agent",
					"code": agent_code,
					"freight_agent_name": agent_code,
					"customer": agent_customer,
				}
			).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Freight Agent", agent_code, "customer", agent_customer)

		doc = frappe._dict(
			local_customer=parent_customer,
			shipper=shipper_code,
			consignee=consignee_code,
			freight_agent=agent_code,
		)

		eligible = get_eligible_bill_to_customers(doc)
		self.assertEqual(
			set(eligible),
			{parent_customer, shipper_customer, consignee_customer, agent_customer},
		)
