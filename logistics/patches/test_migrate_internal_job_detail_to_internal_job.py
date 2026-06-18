# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Idempotency + parameter preservation tests for the Internal Job migration patch.

The patch promotes every legacy ``Internal Job Detail`` row to a top-level ``Internal Job``
record carrying the same parameters + a back-link to the parent booking. The DB-only call path
``frappe.db.sql`` + ``frappe.db.set_value`` is exercised here, with mocked DB primitives so the
test does not require an actual database.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from frappe.tests.utils import FrappeTestCase

from logistics.patches.v2_0_migrate_internal_job_detail_to_internal_job import execute


_DESC_COLUMNS = (
	("name",),
	("parenttype",),
	("parent",),
	("internal_job",),
	("service_type",),
	("job_type",),
	("job_no",),
	("origin_port",),
	("destination_port",),
	("airline",),
	("shipping_line",),
	("transport_mode",),
	("customs_authority",),
	("declaration_type",),
)


_PATCH_MODULE = "logistics.patches.v2_0_migrate_internal_job_detail_to_internal_job"


def _mock_inserted_ij(name):
	ij = MagicMock()
	ij.name = name
	ij.flags = MagicMock()
	return ij


class TestMigrateInternalJobDetailPatch(FrappeTestCase):
	def test_idempotent_skip_when_internal_job_already_set(self):
		"""Rows already migrated (internal_job populated) must not be re-inserted."""
		with patch(f"{_PATCH_MODULE}.frappe.db.table_exists", return_value=True), \
			patch(f"{_PATCH_MODULE}.frappe.db.commit"), \
			patch(
				f"{_PATCH_MODULE}.frappe.db.sql",
				side_effect=[_DESC_COLUMNS, _DESC_COLUMNS, []],
			), \
			patch(f"{_PATCH_MODULE}.frappe.get_doc") as p_get, \
			patch(f"{_PATCH_MODULE}.frappe.db.set_value") as p_set:
			execute()
			p_get.assert_not_called()
			p_set.assert_not_called()

	def test_creates_internal_job_per_legacy_row(self):
		"""Each legacy row is promoted to a new Internal Job; back-link + params copied."""
		legacy_rows = [
			{
				"name": "IJD-A",
				"parenttype": "Sea Booking",
				"parent": "SB-001",
				"service_type": "Sea",
				"origin_port": "MNL",
				"destination_port": "SIN",
				"shipping_line": "MAERSK",
				"transport_mode": "",
				"customs_authority": "",
				"declaration_type": "",
				"airline": "",
				"job_type": "Sea Booking",
				"job_no": "SB-100",
			},
			{
				"name": "IJD-B",
				"parenttype": "Air Booking",
				"parent": "AB-001",
				"service_type": "Air",
				"airline": "PR",
				"origin_port": "MNL",
				"destination_port": "HKG",
				"job_type": "Air Booking",
				"job_no": "AB-200",
				"shipping_line": "",
				"transport_mode": "",
				"customs_authority": "",
				"declaration_type": "",
			},
		]
		with patch(f"{_PATCH_MODULE}.frappe.db.table_exists", return_value=True), \
			patch(f"{_PATCH_MODULE}.frappe.db.commit"), \
			patch(
				f"{_PATCH_MODULE}.frappe.db.sql",
				side_effect=[_DESC_COLUMNS, _DESC_COLUMNS, legacy_rows],
			), \
			patch(
				f"{_PATCH_MODULE}.frappe.get_doc",
				side_effect=[_mock_inserted_ij("IJ-AAA"), _mock_inserted_ij("IJ-BBB")],
			) as p_get, \
			patch(f"{_PATCH_MODULE}.frappe.db.set_value") as p_set:
			execute()

			self.assertEqual(p_get.call_count, 2)
			first_payload = p_get.call_args_list[0].args[0]
			self.assertEqual(first_payload["doctype"], "Internal Job")
			self.assertEqual(first_payload["parent_booking_type"], "Sea Booking")
			self.assertEqual(first_payload["parent_booking_name"], "SB-001")
			self.assertEqual(first_payload["service_type"], "Sea")
			self.assertEqual(first_payload["origin_port"], "MNL")
			self.assertEqual(first_payload["destination_port"], "SIN")
			self.assertEqual(first_payload["shipping_line"], "MAERSK")
			# Empty-string values are skipped (only non-None copied; "" is treated as a value).
			# Schema columns still pass through if their fetched value is non-None; ""
			# values reach the payload as empty strings.
			self.assertEqual(first_payload.get("transport_mode", ""), "")

			second_payload = p_get.call_args_list[1].args[0]
			self.assertEqual(second_payload["service_type"], "Air")
			self.assertEqual(second_payload["airline"], "PR")

			expected_set_calls = [
				call(
					"Internal Job Detail",
					"IJD-A",
					"internal_job",
					"IJ-AAA",
					update_modified=False,
				),
				call(
					"Internal Job Detail",
					"IJD-B",
					"internal_job",
					"IJ-BBB",
					update_modified=False,
				),
			]
			p_set.assert_has_calls(expected_set_calls, any_order=False)

	def test_skips_when_table_missing(self):
		with patch(
			f"{_PATCH_MODULE}.frappe.db.table_exists", return_value=False
		), patch(f"{_PATCH_MODULE}.frappe.db.sql") as p_sql:
			execute()
			p_sql.assert_not_called()
