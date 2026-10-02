# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import add_days, today

from logistics.customs.permit_matching import (
	append_source_tags,
	apply_rule,
	collect_findings,
	enforce_permit_alerts,
	requirement_covered_by_entity_permit,
)

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

_IGNORE_RULE = {
	"missing_permit": "Ignore",
	"pending_permit": "Ignore",
	"expiring_permit": "Ignore",
	"expired_permit": "Ignore",
}


class IntegrationTestPermitApplication(UnitTestCase):
	"""Permit tags match parties and commodities without a shipment link."""

	def setUp(self):
		self.created = []
		self.company = frappe.db.get_value("Company", {}, "name")
		if not self.company:
			self.skipTest("Company is required")
		self.customer = frappe.db.get_value("Customer", {}, "name")
		if not self.customer:
			self.skipTest("Customer is required")
		suffix = frappe.generate_hash(length=8)
		self.consignee = frappe.get_doc(
			{
				"doctype": "Consignee",
				"code": f"IMP-{suffix}",
				"consignee_name": f"Importer {suffix}",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		self.created.append(("Consignee", self.consignee.name))
		self.other_consignee = frappe.get_doc(
			{
				"doctype": "Consignee",
				"code": f"IMP2-{suffix}",
				"consignee_name": f"Other Importer {suffix}",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		self.created.append(("Consignee", self.other_consignee.name))
		self.commodity_a = frappe.get_doc(
			{
				"doctype": "Commodity",
				"code": f"CMD-A-{suffix}",
				"description": f"Commodity A {suffix}",
				"active": 1,
			}
		).insert(ignore_permissions=True)
		self.created.append(("Commodity", self.commodity_a.name))
		self.commodity_b = frappe.get_doc(
			{
				"doctype": "Commodity",
				"code": f"CMD-B-{suffix}",
				"description": f"Commodity B {suffix}",
				"active": 1,
			}
		).insert(ignore_permissions=True)
		self.created.append(("Commodity", self.commodity_b.name))

	def tearDown(self):
		for name in frappe.get_all(
			"Permit Application",
			filters={"application_number": ["like", "PTAG-%"]},
			pluck="name",
		):
			frappe.delete_doc("Permit Application", name, force=True, ignore_permissions=True)
		for name in frappe.get_all(
			"Permit Type",
			filters={"permit_code": ["like", "PTAG-%"]},
			pluck="name",
		):
			frappe.delete_doc("Permit Type", name, force=True, ignore_permissions=True)
		for doctype, name in reversed(getattr(self, "created", [])):
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
		frappe.db.commit()

	def test_tag_target_required_and_disallowed_tag_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Permit Type",
					"permit_code": f"PTAG-NONE-{frappe.generate_hash(length=6)}",
					"permit_name": "No Targets",
					"applicable_to": "All",
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

		permit_type = self._permit_type(applies_to_importer=1)
		with self.assertRaises(frappe.ValidationError):
			self._application(
				permit_type,
				[{"entity_type": "Commodity", "entity_name": self.commodity_a.name}],
			)

	def test_importer_permit_matches_shipment_without_shipment_tag(self):
		permit_type = self._permit_type(applies_to_importer=1)
		application = self._application(
			permit_type,
			[{"entity_type": "Consignee", "entity_name": self.consignee.name}],
			status="Approved",
			valid_to=add_days(today(), -1),
		)
		doc = self._shipment(consignee=self.consignee.name)
		findings = self._findings(doc, permit_type)
		self.assertEqual([row["condition"] for row in findings], ["expired"])
		self.assertEqual(findings[0]["permit_application"], application.name)
		self.assertFalse(self._findings(self._shipment(consignee=self.other_consignee.name), permit_type))

	def test_commodity_permit_matches_only_that_commodity(self):
		permit_type = self._permit_type(applies_to_commodity=1)
		self._application(
			permit_type,
			[{"entity_type": "Commodity", "entity_name": self.commodity_a.name}],
			status="Approved",
			valid_to=add_days(today(), 5),
		)
		self.assertEqual(
			[row["condition"] for row in self._findings(self._shipment(commodity=self.commodity_a.name), permit_type)],
			["expiring"],
		)
		self.assertFalse(self._findings(self._shipment(commodity=self.commodity_b.name), permit_type))

	def test_company_permit_matches_company_jobs(self):
		permit_type = self._permit_type(applies_to_company=1)
		self._application(
			permit_type,
			[{"entity_type": "Company", "entity_name": self.company}],
			status="Approved",
			valid_to=add_days(today(), 5),
		)
		doc = self._shipment(company=self.company)
		self.assertEqual([row["condition"] for row in self._findings(doc, permit_type)], ["expiring"])
		self.assertNotIn(doc.name, {row.get("permit_application") for row in self._findings(doc, permit_type)})

	def test_alert_rule_ignore_warn_block(self):
		permit_type = self._permit_type(applies_to_importer=1)
		self._application(
			permit_type,
			[{"entity_type": "Consignee", "entity_name": self.consignee.name}],
			status="Expired",
			valid_to=add_days(today(), -3),
		)
		doc = self._shipment(consignee=self.consignee.name)
		findings = self._findings(doc, permit_type)
		self.assertEqual(apply_rule(findings, {**_IGNORE_RULE, "expired_permit": "Ignore"}), [])
		warned = apply_rule(findings, {**_IGNORE_RULE, "expired_permit": "Warn"})
		self.assertEqual(warned[0]["action"], "Warn")
		self.assertEqual(warned[0]["level"], "warning")
		blocked = apply_rule(findings, {**_IGNORE_RULE, "expired_permit": "Block"})
		self.assertEqual(blocked[0]["action"], "Block")
		self.assertEqual(blocked[0]["level"], "danger")
		with self.assertRaises(frappe.ValidationError):
			enforce_permit_alerts(doc, rule={**_IGNORE_RULE, "expired_permit": "Block"})

	def test_create_from_declaration_copies_allowed_tags_only(self):
		permit_type = self._permit_type(applies_to_importer=1, applies_to_customer=1)
		permit_application = frappe.new_doc("Permit Application")
		permit_application.permit_type = permit_type
		source = frappe._dict(
			doctype="Declaration",
			name=f"DECL-{frappe.generate_hash(length=6)}",
			customer=self.customer,
			importer_consignee=self.consignee.name,
			company=self.company,
			commercial_invoice_line_items=[frappe._dict(commodity_code=self.commodity_a.name)],
		)
		append_source_tags(permit_application, source)
		tagged = {(row.entity_type, row.entity_name) for row in permit_application.tags}
		self.assertIn(("Customer", self.customer), tagged)
		self.assertIn(("Consignee", self.consignee.name), tagged)
		self.assertNotIn(("Company", self.company), tagged)
		self.assertFalse(any(row[0] == "Commodity" for row in tagged))

	def test_declaration_requirement_satisfied_by_importer_permit(self):
		permit_type = self._permit_type(applies_to_importer=1, applicable_to="Import")
		self._application(
			permit_type,
			[{"entity_type": "Consignee", "entity_name": self.consignee.name}],
			status="Approved",
			valid_to=add_days(today(), 40),
		)
		covered = frappe._dict(
			doctype="Declaration",
			name=f"DECL-{frappe.generate_hash(length=6)}",
			declaration_type="Import",
			importer_consignee=self.consignee.name,
			commercial_invoice_line_items=[frappe._dict(commodity_code=self.commodity_a.name)],
		)
		self.assertTrue(requirement_covered_by_entity_permit(covered, permit_type))
		covered.importer_consignee = self.other_consignee.name
		self.assertFalse(requirement_covered_by_entity_permit(covered, permit_type))

	def _permit_type(self, applicable_to="All", **flags):
		doc = frappe.get_doc(
			{
				"doctype": "Permit Type",
				"permit_code": f"PTAG-{frappe.generate_hash(length=8)}",
				"permit_name": "Tagged Permit",
				"applicable_to": applicable_to,
				"is_active": 1,
				**flags,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _application(self, permit_type, tags, status="Draft", valid_to=None):
		doc = frappe.get_doc(
			{
				"doctype": "Permit Application",
				"permit_type": permit_type,
				"status": "Draft",
				"application_date": today(),
				"application_number": f"PTAG-{frappe.generate_hash(length=8)}",
				"applicant_type": "Customer",
				"applicant": self.customer,
				"company": self.company,
				"tags": tags,
			}
		)
		doc.insert(ignore_permissions=True)
		if status != "Draft" or valid_to:
			frappe.db.set_value(
				"Permit Application",
				doc.name,
				{"status": status, "valid_to": valid_to},
				update_modified=False,
			)
		return doc

	def _shipment(self, consignee=None, commodity=None, company=None):
		return frappe._dict(
			doctype="Air Shipment",
			name=f"AS-PTAG-{frappe.generate_hash(length=6)}",
			consignee=consignee,
			company=company,
			packages=[frappe._dict(commodity=commodity)] if commodity else [],
		)

	def _findings(self, doc, permit_type):
		return [row for row in collect_findings(doc, warn_days=30) if row.get("permit_type") == permit_type]
