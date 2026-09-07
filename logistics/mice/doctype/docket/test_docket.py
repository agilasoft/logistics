# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, today

from logistics.mice.doctype.docket.docket import (
	aggregate_volume_from_packages_remote,
	get_recommended_booth_numbers,
)
from logistics.mice.doctype.docket.docket_booking_creation import _copy_docket_containers_to_target
from logistics.utils.container_validation import calculate_iso6346_check_digit


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestDocket(IntegrationTestCase):
	"""
	Integration tests for Docket.
	Use this class for testing interactions between multiple components.
	"""

	def _test_customer(self):
		return frappe.db.get_value("Customer", {}, "name")

	def _test_organizer(self, name_hint="Test Docket Organizer"):
		customer = self._test_customer()
		if not customer:
			return None
		existing = frappe.db.get_value(
			"MICE Organizer", {"organizer_name": name_hint}, "name"
		)
		if existing:
			return existing
		doc = frappe.new_doc("MICE Organizer")
		doc.organizer_name = name_hint
		doc.organizer_type = "Company"
		doc.customer = customer
		doc.insert(ignore_permissions=True)
		return doc.name

	def _minimal_exhibit(self, project_name="Test Exhibit"):
		organizer = self._test_organizer()
		if not organizer:
			self.skipTest("No Customer in system (organizer needs a backing Customer)")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = project_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit, exhibitor=None, booth_no=None, docstatus=0):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibitor = exhibitor or self._test_customer()
		if not exhibitor:
			self.skipTest("No Customer in system")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit
		dk.exhibitor = exhibitor
		if booth_no is not None:
			dk.booth_no = booth_no
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		if docstatus == 2:
			dk.cancel()
		return dk

	def test_booth_no_unique_per_exhibit_including_cancelled(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Booth Unique Exhibit")
		try:
			d1 = self._minimal_docket(exhibit.name, booth_no="HALL3-09")
			self.addCleanup(lambda: d1.delete(ignore_permissions=True))

			# Cancel the first docket; booth should still be blocked for reuse.
			d1.cancel()

			d2 = frappe.new_doc("Docket")
			d2.exhibit = exhibit.name
			d2.exhibitor = self._test_customer()
			d2.booth_no = "HALL3-09"
			d2.flags.ignore_mandatory = True
			with self.assertRaises(frappe.ValidationError):
				d2.insert(ignore_permissions=True)
		finally:
			exhibit.delete(ignore_permissions=True)

	def test_docket_db_load_initializes_linked_services_for_version_diff(self):
		"""Fresh DB loads must not leave ``linked_services`` as None (breaks submit/version diff)."""
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibit = self._minimal_exhibit("Test Docket Version Diff Exhibit")
		dk = None
		try:
			dk = self._minimal_docket(exhibit.name)
			reloaded = frappe.get_doc("Docket", dk.name)
			self.assertEqual(reloaded.get("linked_services"), [])

			from frappe.core.doctype.version.version import get_diff

			get_diff(reloaded, reloaded)
		finally:
			if dk and dk.name and frappe.db.exists("Docket", dk.name):
				dk.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_get_recommended_booth_numbers_increments_last_number_and_pages(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Booth Suggest Exhibit")
		try:
			seed = self._minimal_docket(exhibit.name, booth_no="HALL3-09")
			self.addCleanup(lambda: seed.delete(ignore_permissions=True))

			# Mark a couple as used so recommender skips them.
			used1 = self._minimal_docket(exhibit.name, exhibitor=self._test_customer(), booth_no="HALL3-10")
			self.addCleanup(lambda: used1.delete(ignore_permissions=True))
			used2 = self._minimal_docket(exhibit.name, exhibitor=self._test_customer(), booth_no="HALL3-12")
			self.addCleanup(lambda: used2.delete(ignore_permissions=True))

			r1 = get_recommended_booth_numbers(exhibit.name, start=0, limit=10)
			s1 = r1.get("suggestions") or []
			self.assertTrue(s1)
			self.assertNotIn("HALL3-10", s1)
			self.assertNotIn("HALL3-12", s1)
			self.assertEqual(s1[0], "HALL3-11")  # 10 used; next is 11

			next_start = r1.get("next_start")
			r2 = get_recommended_booth_numbers(exhibit.name, start=next_start, limit=10)
			s2 = r2.get("suggestions") or []
			self.assertTrue(s2)
			# Ensure paging advances (no overlap at start of list)
			self.assertNotEqual(s1[0], s2[0])
		finally:
			exhibit.delete(ignore_permissions=True)

	def test_docket_has_linked_services_field(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		meta = frappe.get_meta("Docket")
		self.assertTrue(meta.has_field("linked_services"))
		self.assertFalse(meta.has_field("internal_jobs"))

	def test_docket_meta_has_no_customer_link_filters(self):
		"""Regression #1249: Customer.disabled link_filters require Customer.0 read."""
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		meta = frappe.get_meta("Docket")
		for fieldname in ("exhibitor", "customer"):
			df = meta.get_field(fieldname)
			self.assertIsNotNone(df, f"missing field {fieldname}")
			self.assertFalse(
				df.link_filters,
				f"{fieldname} must not use Customer link_filters (permission error Customer.0)",
			)

	def test_sync_customer_from_exhibit_organizer_sets_ignore_links(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibit = self._minimal_exhibit("Test Docket Customer Sync")
		dk = None
		try:
			dk = frappe.new_doc("Docket")
			dk.exhibit = exhibit.name
			dk.exhibitor = self._test_customer()
			dk._sync_customer_from_exhibit_organizer()
			self.assertTrue(getattr(dk.flags, "ignore_links", False))
		finally:
			if dk and dk.name and frappe.db.exists("Docket", dk.name):
				dk.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_calculate_chargeable_weight_higher_of_both_iata(self):
		"""Dense cargo: actual weight wins over volumetric weight."""
		from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")

		dk = frappe.new_doc("Docket")
		dk.total_volume = 0.03
		dk.total_weight = 500
		dk.calculate_chargeable_weight()
		# volume_weight ≈ 0.03 * 166.67 ≈ 5 kg; chargeable = max(500, 5) = 500
		self.assertAlmostEqual(flt(dk.chargeable), 500.0, places=2)
		self.assertGreater(flt(dk.total_weight), flt(dk.total_volume) * IATA_VOLUMETRIC_DENSITY_KG_M3)

	def test_calculate_chargeable_weight_volumetric_wins(self):
		"""Light/bulky cargo: volumetric weight wins."""
		from logistics.utils.measurements import IATA_VOLUMETRIC_DENSITY_KG_M3

		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")

		dk = frappe.new_doc("Docket")
		dk.total_volume = 1.2
		dk.total_weight = 50
		dk.calculate_chargeable_weight()
		expected = 1.2 * IATA_VOLUMETRIC_DENSITY_KG_M3  # ≈ 200 kg
		self.assertAlmostEqual(flt(dk.chargeable), expected, places=4)

	def test_update_packing_summary_sets_chargeable_from_packages(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		if not frappe.db.exists("DocType", "Docket Package"):
			self.skipTest("Docket Package DocType not installed")

		dk = frappe.new_doc("Docket")
		dk.append(
			"packages",
			{"commodity": "TEST", "volume": 0.03, "weight": 500, "no_of_packs": 1},
		)
		dk._update_packing_summary()
		self.assertAlmostEqual(flt(dk.total_volume), 0.03, places=4)
		self.assertAlmostEqual(flt(dk.total_weight), 500.0, places=2)
		self.assertAlmostEqual(flt(dk.chargeable), 500.0, places=2)

	def test_apply_uom_defaults_populates_summary_uoms(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")

		from logistics.utils.measurements import get_default_uoms

		defaults = get_default_uoms()
		if not defaults.get("volume") and not defaults.get("weight"):
			self.skipTest("Logistics UOM defaults not configured")

		dk = frappe.new_doc("Docket")
		dk._apply_uom_defaults()
		if defaults.get("volume"):
			self.assertTrue(dk.total_volume_uom)
		if defaults.get("weight"):
			self.assertTrue(dk.total_weight_uom)
			self.assertTrue(dk.chargeable_weight_uom)

	def test_override_volume_weight_preserves_manual_totals(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		if not frappe.db.exists("DocType", "Docket Package"):
			self.skipTest("Docket Package DocType not installed")

		dk = frappe.new_doc("Docket")
		dk.override_volume_weight = 1
		dk.total_volume = 99
		dk.total_weight = 888
		dk.append(
			"packages",
			{"commodity": "TEST", "volume": 0.03, "weight": 500, "no_of_packs": 1},
		)
		dk._update_packing_summary()
		self.assertAlmostEqual(flt(dk.total_volume), 99.0, places=4)
		self.assertAlmostEqual(flt(dk.total_weight), 888.0, places=2)

	def _test_container_type_with_teu(self, teu=2.0):
		existing = frappe.db.get_value(
			"Container Type", {"active": 1, "teu_count": teu}, "name"
		)
		if existing:
			return existing
		suffix = frappe.generate_hash(length=6)
		doc = frappe.get_doc(
			{
				"doctype": "Container Type",
				"code": f"T-DK-{suffix}",
				"description": "Test container type for docket",
				"active": 1,
				"teu_count": teu,
				"max_gross_weight": 20000,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _iso_container(self, serial6: str) -> str:
		base = "MSCU" + serial6
		return base + str(calculate_iso6346_check_digit(base + "0"))

	def test_update_packing_summary_sets_container_totals(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		if not frappe.db.exists("DocType", "Docket Containers"):
			self.skipTest("Docket Containers DocType not installed")

		ct = self._test_container_type_with_teu(2.0)
		dk = frappe.new_doc("Docket")
		dk.append("containers", {"type": ct, "size": "40ft"})
		dk.append("containers", {"type": ct, "size": "20ft"})
		dk._update_packing_summary()
		self.assertEqual(dk.total_containers, 2)
		self.assertAlmostEqual(flt(dk.total_teus), 4.0, places=2)

	def test_container_cargo_rollup_from_packages(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")

		cn = self._iso_container("888888")
		ct = self._test_container_type_with_teu(1.0)
		dk = frappe.new_doc("Docket")
		dk.append(
			"containers",
			{"container_no": cn, "type": ct, "size": "20ft"},
		)
		dk.append(
			"packages",
			{
				"container": cn,
				"no_of_packs": 3,
				"weight": 120,
				"volume": 0.8,
			},
		)
		dk._update_packing_summary()
		row = dk.containers[0]
		self.assertEqual(row.packages_in_container, 3)
		self.assertAlmostEqual(flt(row.weight_in_container), 120.0, places=2)
		self.assertAlmostEqual(flt(row.volume_in_container), 0.8, places=3)

	def test_aggregate_volume_remote_returns_container_totals(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")

		ct = self._test_container_type_with_teu(1.0)
		dk = frappe.new_doc("Docket")
		dk.append("containers", {"type": ct, "size": "20ft"})
		result = aggregate_volume_from_packages_remote(doc=dk.as_dict())
		self.assertEqual(result.get("total_containers"), 1)
		self.assertAlmostEqual(flt(result.get("total_teus")), 1.0, places=2)

	def test_copy_docket_containers_to_sea_booking(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		if not frappe.db.exists("DocType", "Sea Booking"):
			self.skipTest("Sea Booking DocType not installed")

		ct = self._test_container_type_with_teu(1.0)
		dk = frappe.new_doc("Docket")
		dk.shipping_status = "Booking Confirmed"
		dk.append(
			"containers",
			{
				"type": ct,
				"size": "20ft",
				"mode": frappe.db.get_value("Load Type", {"sea": 1, "is_active": 1}, "name"),
				"delivery_modes": "CY/CY",
				"free_time_days": 5,
			},
		)
		booking = frappe.new_doc("Sea Booking")
		_copy_docket_containers_to_target(dk, booking)
		self.assertEqual(booking.shipping_status, "Booking Confirmed")
		self.assertEqual(len(booking.containers or []), 1)
		self.assertEqual(booking.containers[0].type, ct)
		self.assertEqual(booking.containers[0].size, "20ft")
		self.assertAlmostEqual(flt(booking.containers[0].free_time_days), 5.0, places=2)
