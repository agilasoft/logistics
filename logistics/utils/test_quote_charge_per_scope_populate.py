# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Unit tests for the per-scope Sales Quote -> booking charge extractor.

Covered behaviour:

* A booking with no Internal Jobs receives only Main-scoped rows.
* A booking with linked Internal Jobs receives Main + per-IJ rows, with the same
  underlying Sales Quote Charge row appearing multiple times (once per matching scope)
  when its parameters are wide enough.
* Cross-mode guard rejects an Air-typed Sales Quote Charge on a Sea Booking (and vice versa).
* ``stamp_scope_fields_on_charge_row`` sets ``charge_scope`` / ``internal_job`` on the
  appended booking child row.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from logistics.utils.sales_quote_charge_copy import (
	SCOPE_INTERNAL_JOB,
	SCOPE_MAIN,
	populate_charges_from_quote_by_scope,
	stamp_main_or_internal_job_scope_on_booking_charges,
	stamp_scope_fields_on_charge_row,
)


def _mock_quote(rows):
	q = MagicMock()
	q.charges = rows
	return q


def _mock_sea_booking(origin_port="", shipping_line=""):
	b = MagicMock()
	b.doctype = "Sea Booking"
	b.name = "SB-TEST-0001"
	b.origin_port = origin_port
	b.destination_port = ""
	b.shipping_line = shipping_line
	b.transport_mode = ""
	b.load_type = ""
	b.direction = ""
	b.sea_house_type = ""
	b.freight_agent_sea = ""
	b.airline = ""
	b.air_house_type = ""
	b.freight_agent = ""
	return b


def _mock_air_booking(origin_port="", airline=""):
	b = MagicMock()
	b.doctype = "Air Booking"
	b.name = "AB-TEST-0001"
	b.origin_port = origin_port
	b.destination_port = ""
	b.airline = airline
	b.air_house_type = ""
	b.freight_agent = ""
	b.load_type = ""
	b.direction = ""
	b.shipping_line = ""
	b.transport_mode = ""
	b.sea_house_type = ""
	b.freight_agent_sea = ""
	return b


def _mock_quote_row(name, service_type, **params):
	r = MagicMock()
	r.name = name
	r.service_type = service_type
	for k in (
		"airline", "air_house_type", "freight_agent", "shipping_line", "sea_house_type",
		"freight_agent_sea", "transport_mode", "load_type", "direction",
		"origin_port", "destination_port", "transport_template", "vehicle_type",
		"container_type", "container_no", "location_type", "location_from",
		"location_to", "pick_mode", "drop_mode", "customs_authority",
		"declaration_type", "customs_broker", "customs_charge_category",
		"sp_site", "sp_manpower", "sp_skilled", "sp_equipment_type",
		"sp_handling", "sp_resource_notes", "charge_group",
	):
		setattr(r, k, params.get(k, ""))
	return r


def _mock_internal_job(name, service_type, **params):
	ij = MagicMock()
	ij.name = name
	ij.doctype = "Internal Job"
	ij.service_type = service_type
	for k in (
		"airline", "air_house_type", "freight_agent", "shipping_line", "sea_house_type",
		"freight_agent_sea", "transport_mode", "load_type", "direction",
		"origin_port", "destination_port", "transport_template", "vehicle_type",
		"container_type", "container_no", "location_type", "location_from",
		"location_to", "pick_mode", "drop_mode", "customs_authority",
		"declaration_type", "customs_broker", "customs_charge_category",
	):
		setattr(ij, k, params.get(k, ""))
	return ij


class TestPopulateChargesFromQuoteByScope(FrappeTestCase):
	def _collect_calls(self, parent, quote, internal_jobs):
		calls: list[tuple[object, str, str | None]] = []

		def _append(row, scope, internal_job):
			calls.append((row, scope, internal_job))

		with patch(
			"logistics.utils.internal_job_persistence.get_internal_jobs_for_booking",
			return_value=internal_jobs,
		):
			populate_charges_from_quote_by_scope(parent, quote, _append)
		return calls

	def test_main_only_when_no_internal_jobs(self):
		quote = _mock_quote([
			_mock_quote_row("SQR-1", "Sea", origin_port="MNL"),
			_mock_quote_row("SQR-2", "Sea", origin_port="SIN"),
		])
		parent = _mock_sea_booking(origin_port="MNL")

		calls = self._collect_calls(parent, quote, internal_jobs=[])

		self.assertEqual(len(calls), 1)
		row, scope, ij = calls[0]
		self.assertEqual(row.name, "SQR-1")
		self.assertEqual(scope, SCOPE_MAIN)
		self.assertIsNone(ij)

	def test_duplicates_per_scope_for_wildcard_row(self):
		"""A row with no params matches Main and every Internal Job - appears once per scope."""
		quote = _mock_quote([
			_mock_quote_row("WILD", "Sea"),  # no constraints
			_mock_quote_row("HOME-PORT-MNL", "Sea", origin_port="MNL"),
			_mock_quote_row("HOME-PORT-CEB", "Sea", origin_port="CEB"),
		])
		parent = _mock_sea_booking(origin_port="MNL")
		ij_a = _mock_internal_job("IJ-A", "Sea", origin_port="MNL")
		ij_b = _mock_internal_job("IJ-B", "Sea", origin_port="CEB")

		calls = self._collect_calls(parent, quote, internal_jobs=[ij_a, ij_b])

		# WILD: Main + IJ-A + IJ-B; MNL: Main + IJ-A; CEB: IJ-B only.
		buckets = {(c[0].name, c[1], c[2]) for c in calls}
		self.assertIn(("WILD", SCOPE_MAIN, None), buckets)
		self.assertIn(("WILD", SCOPE_INTERNAL_JOB, "IJ-A"), buckets)
		self.assertIn(("WILD", SCOPE_INTERNAL_JOB, "IJ-B"), buckets)
		self.assertIn(("HOME-PORT-MNL", SCOPE_MAIN, None), buckets)
		self.assertIn(("HOME-PORT-MNL", SCOPE_INTERNAL_JOB, "IJ-A"), buckets)
		self.assertIn(("HOME-PORT-CEB", SCOPE_INTERNAL_JOB, "IJ-B"), buckets)
		self.assertNotIn(("HOME-PORT-CEB", SCOPE_MAIN, None), buckets)
		self.assertNotIn(("HOME-PORT-CEB", SCOPE_INTERNAL_JOB, "IJ-A"), buckets)
		self.assertNotIn(("HOME-PORT-MNL", SCOPE_INTERNAL_JOB, "IJ-B"), buckets)

	def test_cross_mode_guard_rejects_air_row_on_sea_booking(self):
		quote = _mock_quote([
			_mock_quote_row("AIR-ROW", "Air", origin_port="MNL"),
			_mock_quote_row("SEA-ROW", "Sea", origin_port="MNL"),
		])
		parent = _mock_sea_booking(origin_port="MNL")

		calls = self._collect_calls(parent, quote, internal_jobs=[])

		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0][0].name, "SEA-ROW")
		self.assertEqual(calls[0][1], SCOPE_MAIN)

	def test_cross_mode_guard_rejects_sea_row_on_air_booking(self):
		quote = _mock_quote([
			_mock_quote_row("AIR-ROW", "Air", airline="PR"),
			_mock_quote_row("SEA-ROW", "Sea", shipping_line="MAERSK"),
		])
		parent = _mock_air_booking(airline="PR")

		calls = self._collect_calls(parent, quote, internal_jobs=[])

		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0][0].name, "AIR-ROW")
		self.assertEqual(calls[0][1], SCOPE_MAIN)

	def test_internal_job_scope_only_when_main_does_not_match(self):
		quote = _mock_quote([
			_mock_quote_row("ONLY-CEB", "Sea", origin_port="CEB"),
		])
		parent = _mock_sea_booking(origin_port="MNL")
		ij = _mock_internal_job("IJ-CEB", "Sea", origin_port="CEB")

		calls = self._collect_calls(parent, quote, internal_jobs=[ij])

		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0][1], SCOPE_INTERNAL_JOB)
		self.assertEqual(calls[0][2], "IJ-CEB")

	def test_internal_job_service_type_must_match_row(self):
		"""A Sea quote row never lands on a Customs Internal Job (service type mismatch)."""
		quote = _mock_quote([
			_mock_quote_row("SEA-ROW", "Sea", origin_port="MNL"),
		])
		parent = _mock_sea_booking(origin_port="MNL")
		ij = _mock_internal_job("IJ-CUSTOMS", "Customs", customs_authority="BOC")

		calls = self._collect_calls(parent, quote, internal_jobs=[ij])

		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0][1], SCOPE_MAIN)


class TestStampScopeFieldsOnChargeRow(FrappeTestCase):
	def test_dict_row_stamping(self):
		row = {}
		stamp_scope_fields_on_charge_row(row, SCOPE_MAIN, None)
		self.assertEqual(row.get("charge_scope"), SCOPE_MAIN)
		self.assertIsNone(row.get("internal_job"))

	def test_dict_row_internal_job_stamping(self):
		row = {}
		stamp_scope_fields_on_charge_row(row, SCOPE_INTERNAL_JOB, "IJ-XYZ")
		self.assertEqual(row.get("charge_scope"), SCOPE_INTERNAL_JOB)
		self.assertEqual(row.get("internal_job"), "IJ-XYZ")

	def test_object_row_only_writes_existing_fields(self):
		row = MagicMock(doctype="Sea Booking Charges")
		meta = MagicMock()
		meta.has_field.side_effect = lambda fn: fn in {"charge_scope", "internal_job"}
		with patch(
			"logistics.utils.sales_quote_charge_copy.frappe.get_meta", return_value=meta
		):
			stamp_scope_fields_on_charge_row(row, SCOPE_INTERNAL_JOB, "IJ-Z")
		self.assertEqual(row.charge_scope, SCOPE_INTERNAL_JOB)
		self.assertEqual(row.internal_job, "IJ-Z")


def _make_meta(parent_dt: str, child_dt: str, *, has_scope=True, has_ij=True) -> MagicMock:
	"""Build the parent + child meta pair returned by ``frappe.get_meta`` patches."""
	parent_meta = MagicMock()
	charges_df = MagicMock()
	charges_df.options = child_dt
	parent_meta.get_field.side_effect = lambda fn: charges_df if fn == "charges" else None

	child_meta = MagicMock()
	allowed: set[str] = set()
	if has_scope:
		allowed.add("charge_scope")
	if has_ij:
		allowed.add("internal_job")
	child_meta.has_field.side_effect = lambda fn: fn in allowed

	def _get_meta(name):
		if name == parent_dt:
			return parent_meta
		if name == child_dt:
			return child_meta
		raise ValueError(f"unexpected meta lookup: {name}")

	return _get_meta


def _make_charge_row(**fields) -> MagicMock:
	"""Mock charge row that round-trips ``charge_scope`` / ``internal_job`` like a real Document row."""
	row = MagicMock()
	row.charge_scope = fields.get("charge_scope", "")
	row.internal_job = fields.get("internal_job", "")
	for k, v in fields.items():
		setattr(row, k, v)
	return row


class TestStampMainOrInternalJobScopeOnBookingCharges(FrappeTestCase):
	"""Default-stamp helper applied at the end of validate on each booking that owns charges."""

	def test_main_booking_fills_empty_scope_with_main(self):
		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 0
		parent.charges = [_make_charge_row(), _make_charge_row()]

		with patch(
			"logistics.utils.sales_quote_charge_copy.frappe.get_meta",
			side_effect=_make_meta("Sea Booking", "Sea Booking Charges"),
		):
			stamp_main_or_internal_job_scope_on_booking_charges(parent)

		for row in parent.charges:
			self.assertEqual(row.charge_scope, SCOPE_MAIN)

	def test_main_booking_preserves_explicit_internal_job_scope(self):
		"""Pre-stamped IJ rows on a Main booking must stay (e.g. dialog flow / per-scope copy)."""
		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 0
		ij_row = _make_charge_row(charge_scope=SCOPE_INTERNAL_JOB, internal_job="IJ-A")
		main_row = _make_charge_row()
		parent.charges = [main_row, ij_row]

		with patch(
			"logistics.utils.sales_quote_charge_copy.frappe.get_meta",
			side_effect=_make_meta("Sea Booking", "Sea Booking Charges"),
		):
			stamp_main_or_internal_job_scope_on_booking_charges(parent)

		self.assertEqual(main_row.charge_scope, SCOPE_MAIN)
		self.assertEqual(ij_row.charge_scope, SCOPE_INTERNAL_JOB)
		self.assertEqual(ij_row.internal_job, "IJ-A")

	def test_internal_job_booking_overwrites_inherited_main_scope(self):
		"""IJ booking that inherits Main-scope rows from a copy gets re-tagged Internal Job."""
		parent = MagicMock()
		parent.doctype = "Sea Booking"
		parent.is_internal_job = 1
		parent.main_job_type = "Sea Booking"
		parent.main_job = "SB-MAIN"
		parent.name = "SB-IJ-001"
		# Two rows: one stamped IJ but with a stale link (e.g. cloned from another IJ booking),
		# one inherited as Main from main-job copy.
		clone_row = _make_charge_row(charge_scope=SCOPE_INTERNAL_JOB, internal_job="IJ-OTHER")
		stale_row = _make_charge_row(charge_scope=SCOPE_MAIN)
		parent.charges = [clone_row, stale_row]

		with patch(
			"logistics.utils.sales_quote_charge_copy.frappe.get_meta",
			side_effect=_make_meta("Sea Booking", "Sea Booking Charges"),
		), patch(
			"logistics.utils.internal_job_persistence.resolve_internal_job_for_internal_job_booking",
			return_value="IJ-RESOLVED",
		):
			stamp_main_or_internal_job_scope_on_booking_charges(parent)

		# Both rows now report Internal Job scope; both link to the booking's own resolved IJ.
		self.assertEqual(clone_row.charge_scope, SCOPE_INTERNAL_JOB)
		self.assertEqual(clone_row.internal_job, "IJ-RESOLVED")
		self.assertEqual(stale_row.charge_scope, SCOPE_INTERNAL_JOB)
		self.assertEqual(stale_row.internal_job, "IJ-RESOLVED")

	def test_no_op_when_child_table_lacks_scope_fields(self):
		"""Booking child tables without ``charge_scope`` / ``internal_job`` are not touched."""
		parent = MagicMock()
		parent.doctype = "Special Project"
		parent.is_internal_job = 0
		row = _make_charge_row()
		parent.charges = [row]

		with patch(
			"logistics.utils.sales_quote_charge_copy.frappe.get_meta",
			side_effect=_make_meta(
				"Special Project",
				"Special Project Charges",
				has_scope=False,
				has_ij=False,
			),
		):
			stamp_main_or_internal_job_scope_on_booking_charges(parent)

		# Helper bailed before stamping; row stays as-is.
		self.assertEqual(row.charge_scope, "")
