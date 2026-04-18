# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Unit tests for parent DG compliance status helper."""

from types import SimpleNamespace

from frappe.tests.utils import FrappeTestCase

from logistics.utils.dg_fields import (
	DG_STATUS_PENDING_DOCUMENTATION,
	update_parent_dg_compliance_status,
)


class TestUpdateParentDgComplianceStatus(FrappeTestCase):
	"""Pure helper; no DB."""

	def tearDown(self):
		import frappe

		frappe.db.rollback()

	def _doc(self, **kwargs):
		base = dict(
			contains_dangerous_goods=1,
			dg_declaration_complete=0,
			dg_compliance_status="",
			dg_emergency_contact="",
			dg_emergency_phone="",
			dg_emergency_email="",
		)
		base.update(kwargs)
		return SimpleNamespace(**base)

	def test_no_dangerous_goods_clears_status(self):
		d = self._doc(contains_dangerous_goods=0, dg_compliance_status="Compliant")
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "")

	def test_declaration_incomplete_under_review(self):
		d = self._doc(dg_declaration_complete=0)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "Under Review")

	def test_declaration_complete_missing_fields_non_compliant(self):
		d = self._doc(
			dg_declaration_complete=1,
			dg_emergency_contact="A",
			dg_emergency_phone="",
			dg_emergency_email="a@b.com",
		)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "Non-Compliant")

	def test_declaration_complete_all_fields_compliant(self):
		d = self._doc(
			dg_declaration_complete=1,
			dg_emergency_contact="Name",
			dg_emergency_phone="+1",
			dg_emergency_email="x@y.com",
		)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "Compliant")

	def test_whitespace_only_emergency_counts_as_empty(self):
		d = self._doc(
			dg_declaration_complete=1,
			dg_emergency_contact="  ",
			dg_emergency_phone="1",
			dg_emergency_email="a@b.com",
		)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "Non-Compliant")

	def test_preserves_pending_documentation_when_under_review(self):
		d = self._doc(
			dg_declaration_complete=0,
			dg_compliance_status=DG_STATUS_PENDING_DOCUMENTATION,
		)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, DG_STATUS_PENDING_DOCUMENTATION)

	def test_pending_documentation_cleared_when_declaration_complete(self):
		d = self._doc(
			dg_declaration_complete=1,
			dg_compliance_status=DG_STATUS_PENDING_DOCUMENTATION,
			dg_emergency_contact="N",
			dg_emergency_phone="P",
			dg_emergency_email="e@mail.com",
		)
		update_parent_dg_compliance_status(d)
		self.assertEqual(d.dg_compliance_status, "Compliant")

	def test_skips_when_no_dg_compliance_status_field(self):
		d = SimpleNamespace(contains_dangerous_goods=1, dg_declaration_complete=0)
		update_parent_dg_compliance_status(d)
		self.assertFalse(hasattr(d, "dg_compliance_status"))
