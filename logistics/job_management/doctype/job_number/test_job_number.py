# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

"""Unit tests for Job Number's auto-derivation of ``project`` and ``docket``.

These tests mock ``frappe.db`` / ``frappe.get_meta`` so they can run without
touching the database. They exercise the resolution rules implemented in
``JobNumber._sync_project_and_docket``.
"""

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.job_management.doctype.job_number.job_number import JobNumber


def _make_jcn(**overrides):
	"""Build a JobNumber instance without going through the DB / __init__ heavy lifting."""
	jcn = JobNumber.__new__(JobNumber)
	jcn.job_type = None
	jcn.job_no = None
	jcn.project = None
	jcn.docket = None
	for k, v in overrides.items():
		setattr(jcn, k, v)
	return jcn


class _FakeMeta:
	def __init__(self, fields):
		self._fields = set(fields)

	def has_field(self, name):
		return name in self._fields


class TestJobNumberSyncProjectAndDocket(UnitTestCase):
	def test_no_change_when_job_type_or_no_missing(self):
		jcn = _make_jcn(job_type=None, job_no=None)
		jcn._sync_project_and_docket()
		self.assertIsNone(jcn.project)
		self.assertIsNone(jcn.docket)

		jcn = _make_jcn(job_type="Sea Shipment", job_no=None)
		jcn._sync_project_and_docket()
		self.assertIsNone(jcn.project)
		self.assertIsNone(jcn.docket)

	def test_docket_job_type_mirrors_self_and_pulls_project(self):
		jcn = _make_jcn(job_type="Docket", job_no="D-0001")

		def _exists(dt, name=None):
			return True

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Docket" and name == "D-0001" and fieldname == "project":
				return "PROJ-0001"
			return None

		with (
			patch("frappe.db.exists", side_effect=_exists),
			patch("frappe.db.get_value", side_effect=_get_value),
		):
			jcn._sync_project_and_docket()

		self.assertEqual(jcn.docket, "D-0001")
		self.assertEqual(jcn.project, "PROJ-0001")

	def test_special_project_pulls_project_from_source(self):
		jcn = _make_jcn(job_type="Special Project", job_no="PROJ-0099")

		fake_meta = _FakeMeta({"project"})

		def _exists(dt, name=None):
			return True

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Special Project" and name == "PROJ-0099" and fieldname == "project":
				return "PROJ-0099"
			return None

		with (
			patch("frappe.db.exists", side_effect=_exists),
			patch("frappe.get_meta", return_value=fake_meta),
			patch("frappe.db.get_value", side_effect=_get_value),
			patch("frappe.get_all", return_value=[]),
		):
			jcn._sync_project_and_docket()

		self.assertEqual(jcn.project, "PROJ-0099")
		self.assertIsNone(jcn.docket)

	def test_sea_shipment_finds_docket_via_booking_and_inherits_project(self):
		jcn = _make_jcn(job_type="Sea Shipment", job_no="SSH-001")

		# Sea Shipment has 'project' (blank) + 'sea_booking' fields.
		fake_meta = _FakeMeta({"project", "sea_booking"})

		def _exists(dt, name=None):
			return True

		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Sea Shipment" and name == "SSH-001":
				if fieldname == "project":
					return None  # not set on shipment
				if fieldname == "sea_booking":
					return "SBK-001"
			if dt == "Docket" and name == "D-EXPO" and fieldname == "project":
				return "PROJ-DOCK"
			if dt == "Internal Job Detail":
				# Signature: frappe.db.get_value(doctype, filters_dict, fieldname).
				# Here ``name`` carries the filters dict; ``fieldname`` is "parent".
				filters = name
				if (
					isinstance(filters, dict)
					and filters.get("job_type") == "Sea Booking"
					and filters.get("job_no") == "SBK-001"
				):
					return "D-EXPO"
				return None
			return None

		with (
			patch("frappe.db.exists", side_effect=_exists),
			patch("frappe.get_meta", return_value=fake_meta),
			patch("frappe.db.get_value", side_effect=_get_value),
		):
			jcn._sync_project_and_docket()

		self.assertEqual(jcn.docket, "D-EXPO")
		self.assertEqual(jcn.project, "PROJ-DOCK")

	def test_existing_values_are_preserved(self):
		jcn = _make_jcn(
			job_type="Sea Shipment",
			job_no="SSH-002",
			project="PROJ-KEEP",
			docket="D-KEEP",
		)

		fake_meta = _FakeMeta({"project", "sea_booking"})

		def _exists(dt, name=None):
			return True

		# get_value should never be asked to override project/docket once set.
		def _get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Sea Shipment" and name == "SSH-002" and fieldname == "project":
				raise AssertionError("project lookup should be skipped when already set")
			return None

		with (
			patch("frappe.db.exists", side_effect=_exists),
			patch("frappe.get_meta", return_value=fake_meta),
			patch("frappe.db.get_value", side_effect=_get_value),
		):
			jcn._sync_project_and_docket()

		self.assertEqual(jcn.project, "PROJ-KEEP")
		self.assertEqual(jcn.docket, "D-KEEP")
