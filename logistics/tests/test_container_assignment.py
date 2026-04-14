# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.container_validation import calculate_iso6346_check_digit


def _make_valid_container_no():
	base10 = "MSCU123456"
	cd = calculate_iso6346_check_digit(base10 + "0")
	return base10 + str(cd)


def _make_master_bill(master_bl):
	doc = frappe.get_doc(
		{
			"doctype": "Master Bill",
			"master_bl": master_bl,
			"master_type": "Direct",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def run_smoke():
	"""Manual check: `bench --site logistics.agilasoft.com execute logistics.tests.test_container_assignment.run_smoke`"""
	sfx = frappe.generate_hash(length=6)
	cn = _make_valid_container_no()
	mb1 = _make_master_bill("SMOKE-CA-MBL-{0}-1".format(sfx))
	mb2 = _make_master_bill("SMOKE-CA-MBL-{0}-2".format(sfx))
	a1 = frappe.get_doc(
		{
			"doctype": "Container",
			"container_number": cn,
			"master_bill": mb1,
			"is_active": 1,
		}
	)
	a1.insert(ignore_permissions=True)
	try:
		frappe.get_doc(
			{
				"doctype": "Container",
				"container_number": cn,
				"master_bill": mb2,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
	except frappe.ValidationError:
		pass
	else:
		frappe.throw("expected ValidationError for second active MBL")
	frappe.delete_doc("Container", a1.name, force=True, ignore_permissions=True)
	frappe.delete_doc("Master Bill", mb1, force=True, ignore_permissions=True)
	frappe.delete_doc("Master Bill", mb2, force=True, ignore_permissions=True)
	frappe.db.commit()
	return "ok"


class TestContainerMasterBillAssignment(FrappeTestCase):
	def setUp(self):
		super(TestContainerMasterBillAssignment, self).setUp()
		sfx = frappe.generate_hash(length=6)
		self.cn = _make_valid_container_no()
		self.mb1 = _make_master_bill("TEST-CA-MBL-{0}-1".format(sfx))
		self.mb2 = _make_master_bill("TEST-CA-MBL-{0}-2".format(sfx))

	def tearDown(self):
		frappe.db.rollback()
		super(TestContainerMasterBillAssignment, self).tearDown()

	def _new_container(self, master_bill, container_no=None, is_active=1):
		doc = frappe.get_doc(
			{
				"doctype": "Container",
				"container_number": container_no or self.cn,
				"master_bill": master_bill,
				"is_active": is_active,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_autoname_master_bill_and_container(self):
		doc = self._new_container(self.mb1)
		self.assertTrue(doc.name.startswith(self.mb1))
		self.assertIn(self.cn, doc.name)

	def test_reject_second_active_same_mbl(self):
		self._new_container(self.mb1)
		doc2 = frappe.get_doc(
			{
				"doctype": "Container",
				"container_number": self.cn,
				"master_bill": self.mb1,
				"is_active": 1,
			}
		)
		self.assertRaises(frappe.ValidationError, doc2.insert)

	def test_reject_active_on_second_mbl_while_first_active(self):
		self._new_container(self.mb1)
		doc2 = frappe.get_doc(
			{
				"doctype": "Container",
				"container_number": self.cn,
				"master_bill": self.mb2,
				"is_active": 1,
			}
		)
		self.assertRaises(frappe.ValidationError, doc2.insert)

	def test_allow_second_mbl_after_first_inactive(self):
		first = self._new_container(self.mb1)
		first.is_active = 0
		first.save(ignore_permissions=True)
		second = self._new_container(self.mb2)
		self.assertEqual(
			frappe.db.get_value("Container", second.name, "is_active"),
			1,
		)

	def test_inactive_sets_assignment_inactive_date(self):
		doc = self._new_container(self.mb1)
		doc.is_active = 0
		doc.save(ignore_permissions=True)
		self.assertIsNotNone(doc.assignment_inactive_date)

	def test_get_active_container_assignment_api(self):
		doc = self._new_container(self.mb1)
		from logistics.container_management.api import get_active_container_assignment

		self.assertEqual(get_active_container_assignment(self.cn), doc.name)
