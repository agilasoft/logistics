# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Docket virtual read-only ``linked_services`` grid backed by Linked Service docs."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype


class TestDocketVirtualLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

	def _minimal_exhibit(self, project_name: str):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer in system")
		organizer = frappe.db.get_value("MICE Organizer", {}, "name")
		if not organizer:
			org = frappe.new_doc("MICE Organizer")
			org.organizer_name = f"Test Org {project_name}"
			org.organizer_type = "Company"
			org.customer = customer
			org.insert(ignore_permissions=True)
			organizer = org.name
		# Unique project_name — ERPNext Project keeps the label after MICE Project delete.
		unique_name = f"{project_name} {frappe.generate_hash(length=6)}"
		doc = frappe.new_doc("MICE Project")
		doc.project_name = unique_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit_name: str):
		customer = frappe.db.get_value("Customer", {}, "name")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit_name
		dk.exhibitor = customer
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		return dk

	def test_linked_services_view_from_owned_documents(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS View")
		dk = self._minimal_docket(exhibit.name)
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Air"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			reloaded = frappe.get_doc("Docket", dk.name)
			self.assertEqual(len(reloaded.linked_services), 1)
			self.assertEqual(reloaded.linked_services[0].get("service_type"), "Air")
		finally:
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_staged_sync_creates_linked_service_document(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS Sync")
		dk = self._minimal_docket(exhibit.name)
		try:
			doc = frappe.get_doc("Docket", dk.name)
			frappe.local._logistics_dk_ij_client_rows = [
				frappe._dict({"service_type": "Sea", "job_type": "Sea Booking"})
			]
			sync_internal_job_details_to_internal_jobs(doc)
			names = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), next(iter(names)))
			self.assertEqual(ls.parent_booking_type, "Docket")
			self.assertEqual(ls.parent_booking_name, dk.name)
			self.assertEqual(ls.service_type, "Sea")
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_save_with_virtual_linked_services_does_not_fail_version(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS Version")
		dk = self._minimal_docket(exhibit.name)
		try:
			doc = frappe.get_doc("Docket", dk.name)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			reloaded = frappe.get_doc("Docket", dk.name)
			# Virtual field: use property / helper, not Document.get (returns None).
			self.assertIsInstance(reloaded.linked_services, list)
			reloaded.description = (reloaded.description or "") + " updated"
			reloaded.flags.ignore_mandatory = True
			reloaded.save(ignore_permissions=True)
		finally:
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_persist_job_link_materializes_missing_linked_service_without_save_required(self):
		"""Desk form_rows without Docket-owned LS docs must not throw Save required.

		Simulates Create Booking/Order after a saved Docket whose Linked Services were never
		cloned from the quote: client rows are present, canonical LS docs are empty.
		"""
		from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

		exhibit = self._minimal_exhibit("Docket Persist LS Materialize")
		dk = self._minimal_docket(exhibit.name)
		fake_job_no = f"SB-TEST-{frappe.generate_hash(length=8)}"
		try:
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())
			frappe.local._logistics_dk_ij_client_rows = [
				frappe._dict(
					{
						"service_type": "Sea",
						"job_type": "Sea Booking",
					}
				)
			]
			# Must not raise "Save required" — materializes a Linked Service then writes job_no.
			persist_internal_job_detail_job_link(
				"Docket",
				dk.name,
				"Sea Booking",
				fake_job_no,
				detail_idx=1,
			)
			names = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), list(names)[0])
			self.assertEqual(ls.parent_booking_type, "Docket")
			self.assertEqual(ls.parent_booking_name, dk.name)
			self.assertEqual((ls.job_type or "").strip(), "Sea Booking")
			self.assertEqual((ls.job_no or "").strip(), fake_job_no)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_persist_job_link_empty_client_override_does_not_wipe_linked_services(self):
		"""Empty desk linked_services payload must not orphan-delete existing Docket LS docs.

		Create Booking/Order often sends ``[]`` for the virtual grid; persist must stamp
		``job_no`` without parent-save orphan sync wiping sibling Linked Services.
		"""
		from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

		exhibit = self._minimal_exhibit("Docket Persist LS Wipe Guard")
		dk = self._minimal_docket(exhibit.name)
		fake_job_no = f"SB-TEST-{frappe.generate_hash(length=8)}"
		ls_names: list[str] = []
		try:
			for service_type, job_type in (("Sea", "Sea Booking"), ("Air", "Air Booking")):
				ls = frappe.new_doc(linked_service_doctype())
				ls.parent_booking_type = "Docket"
				ls.parent_booking_name = dk.name
				ls.service_type = service_type
				ls.job_type = job_type
				ls.flags.ignore_mandatory = True
				ls.insert(ignore_permissions=True)
				ls_names.append(ls.name)

			before = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(before, set(ls_names))

			# Simulate Create Booking desk payload: empty virtual grid override.
			frappe.local._logistics_dk_ij_client_rows = []
			persist_internal_job_detail_job_link(
				"Docket",
				dk.name,
				"Sea Booking",
				fake_job_no,
				detail_idx=1,
			)

			after = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(after, set(ls_names))
			sea = frappe.get_doc(linked_service_doctype(), ls_names[0])
			air = frappe.get_doc(linked_service_doctype(), ls_names[1])
			self.assertEqual((sea.job_type or "").strip(), "Sea Booking")
			self.assertEqual((sea.job_no or "").strip(), fake_job_no)
			self.assertEqual((air.job_type or "").strip(), "Air Booking")
			self.assertFalse((air.job_no or "").strip())
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def _minimal_sales_quote_with_linked_services(self, title: str):
		"""Sales Quote owning Sea + Transport Linked Services (for Docket heal tests)."""
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Regular"
		sq.main_service = "Sea"
		sq.naming_series = "SQU.#########"
		sq.customer = frappe.db.get_value("Customer", {}, "name")
		if not sq.customer:
			self.skipTest("No Customer in system")
		sq.shipper = frappe.db.get_value("Shipper", {}, "name")
		sq.consignee = frappe.db.get_value("Consignee", {}, "name")
		if not sq.shipper or not sq.consignee:
			self.skipTest("No Shipper/Consignee in system")
		sq.date = today()
		sq.valid_until = add_days(today(), 30)
		sq.flags.ignore_mandatory = True
		sq.flags.ignore_validate = True
		sq.insert(ignore_permissions=True)
		for service_type, job_type in (("Sea", "Sea Booking"), ("Transport", "Transport Order")):
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Sales Quote"
			ls.parent_booking_name = sq.name
			ls.service_type = service_type
			ls.job_type = job_type
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
		return sq

	def test_get_docket_booking_choices_materializes_from_sales_quote(self):
		"""Empty Docket LS + quote-owned LS → choices materialize Docket clones."""
		from logistics.mice.doctype.docket.docket_booking_creation import (
			get_docket_booking_choices,
		)

		exhibit = self._minimal_exhibit("Docket Choices LS Heal")
		dk = self._minimal_docket(exhibit.name)
		sq = self._minimal_sales_quote_with_linked_services("Docket Choices LS Heal SQ")
		try:
			frappe.db.set_value("Docket", dk.name, "sales_quote", sq.name, update_modified=False)
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 2)

			msg = get_docket_booking_choices(dk.name, linked_services="[]")
			choices = msg.get("choices") or []
			self.assertGreaterEqual(len(choices), 2)
			dk_ls = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(dk_ls), 2)
			# Quote originals remain; Docket clones are distinct.
			self.assertFalse(dk_ls & _linked_service_names_from_db("Sales Quote", sq.name))
			sea_choices = [c for c in choices if c.get("job_type") == "Sea Booking"]
			self.assertTrue(sea_choices)
		finally:
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			for ls_name in _linked_service_names_from_db("Sales Quote", sq.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_docket_onload_materializes_from_sales_quote(self):
		"""Opening a Docket with sales_quote but no LS clones from the quote."""
		exhibit = self._minimal_exhibit("Docket Onload LS Heal")
		dk = self._minimal_docket(exhibit.name)
		sq = self._minimal_sales_quote_with_linked_services("Docket Onload LS Heal SQ")
		try:
			frappe.db.set_value("Docket", dk.name, "sales_quote", sq.name, update_modified=False)
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())

			reloaded = frappe.get_doc("Docket", dk.name)
			reloaded.run_method("onload")
			dk_ls = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(dk_ls), 2)
			self.assertEqual(len(reloaded.linked_services), 2)
		finally:
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			for ls_name in _linked_service_names_from_db("Sales Quote", sq.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_persist_job_link_stub_client_ignores_foreign_linked_service(self):
		"""Desk stub with a Sales Quote LS name must still stamp the Docket-owned LS by idx."""
		from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		exhibit = self._minimal_exhibit("Docket Persist Foreign LS Guard")
		dk = self._minimal_docket(exhibit.name)
		fake_job_no = f"TRO-TEST-{frappe.generate_hash(length=8)}"
		sq_ls_name = None
		dk_ls_name = None
		try:
			sq_ls = frappe.new_doc(linked_service_doctype())
			sq_ls.parent_booking_type = "Sales Quote"
			sq_ls.parent_booking_name = f"SQ-FAKE-{frappe.generate_hash(length=6)}"
			sq_ls.service_type = "Transport"
			sq_ls.job_type = "Transport Order"
			sq_ls.flags.ignore_mandatory = True
			sq_ls.insert(ignore_permissions=True)
			sq_ls_name = sq_ls.name

			dk_ls = frappe.new_doc(linked_service_doctype())
			dk_ls.parent_booking_type = "Docket"
			dk_ls.parent_booking_name = dk.name
			dk_ls.service_type = "Transport"
			dk_ls.job_type = "Transport Order"
			dk_ls.flags.ignore_mandatory = True
			dk_ls.insert(ignore_permissions=True)
			dk_ls_name = dk_ls.name

			# Stale desk payload points at the quote LS (wrong parent).
			frappe.local._logistics_dk_ij_client_rows = [
				frappe._dict(
					{
						"linked_service": sq_ls_name,
						"service_type": "Transport",
						"job_type": "Transport Order",
					}
				)
			]
			persist_internal_job_detail_job_link(
				"Docket",
				dk.name,
				"Transport Order",
				fake_job_no,
				detail_idx=1,
			)

			dk_ls.reload()
			self.assertEqual((dk_ls.job_no or "").strip(), fake_job_no)
			sq_ls.reload()
			self.assertFalse((sq_ls.job_no or "").strip())

			view = build_linked_services_view_for_booking("Docket", dk.name)
			self.assertEqual(len(view), 1)
			self.assertEqual((view[0].get("job_no") or "").strip(), fake_job_no)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			for name in (dk_ls_name, sq_ls_name):
				if name and frappe.db.exists(linked_service_doctype(), name):
					frappe.delete_doc(
						linked_service_doctype(), name, force=True, ignore_permissions=True
					)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_create_transport_order_from_docket_persists_job_no(self):
		"""Docket Create → Transport Order must write Job No onto the Docket Linked Service."""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			create_booking_or_order_from_docket,
		)
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		if not frappe.db.exists("DocType", "Transport Order"):
			self.skipTest("Transport Order not installed")

		exhibit = self._minimal_exhibit("Docket Create TRO Persist")
		dk = self._minimal_docket(exhibit.name)
		self._seed_docket_accounts(dk.name)
		order_name = None
		ls_name = None
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Transport"
			ls.job_type = "Transport Order"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			ls_name = ls.name

			# Stub desk payload (no linked_service name) — persist must resolve by DB idx.
			stub_payload = [
				{
					"service_type": "Transport",
					"job_type": "Transport Order",
				}
			]
			orig_insert = frappe.model.document.Document.insert
			with patch(
				"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible"
			), patch.object(
				frappe.model.document.Document,
				"insert",
				self._insert_ignore_mandatory(orig_insert),
			):
				result = create_booking_or_order_from_docket(
					docket=dk.name,
					job_type="Transport Order",
					internal_job_idx=1,
					linked_services=stub_payload,
				)
			order_name = result.get("transport_order")
			self.assertTrue(order_name)

			ls.reload()
			self.assertEqual((ls.job_type or "").strip(), "Transport Order")
			self.assertEqual((ls.job_no or "").strip(), order_name)

			view = build_linked_services_view_for_booking("Docket", dk.name)
			self.assertEqual(len(view), 1)
			self.assertEqual((view[0].get("job_no") or "").strip(), order_name)

			if frappe.get_meta("Transport Order").has_field("linked_service"):
				tro_ls = frappe.db.get_value("Transport Order", order_name, "linked_service")
				self.assertEqual(tro_ls, ls_name)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			if order_name and frappe.db.exists("Transport Order", order_name):
				frappe.delete_doc("Transport Order", order_name, force=True, ignore_permissions=True)
			if ls_name and frappe.db.exists(linked_service_doctype(), ls_name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def _seed_docket_accounts(self, dk_name: str) -> None:
		"""Copy company / branch / cost center / profit center onto the Docket when present."""
		company = frappe.db.get_value("Company", {}, "name")
		if not company:
			return
		updates = {"company": company}
		branch = frappe.db.get_value("Branch", {}, "name")
		if branch:
			updates["branch"] = branch
		cc = None
		if frappe.db.exists("DocType", "Cost Center"):
			cc = frappe.db.get_value(
				"Cost Center", {"company": company, "is_group": 0}, "name"
			) or frappe.db.get_value("Cost Center", {"company": company}, "name")
		if cc:
			updates["cost_center"] = cc
		pc = None
		if frappe.db.exists("DocType", "Profit Center"):
			pc = frappe.db.get_value("Profit Center", {}, "name")
		if pc:
			updates["profit_center"] = pc
		for fn, val in updates.items():
			if frappe.get_meta("Docket").has_field(fn):
				frappe.db.set_value("Docket", dk_name, fn, val, update_modified=False)

	@staticmethod
	def _insert_ignore_mandatory(orig_insert):
		def _insert(self, *args, **kwargs):
			self.flags.ignore_mandatory = True
			kwargs.setdefault("ignore_mandatory", True)
			return orig_insert(self, *args, **kwargs)

		return _insert

	def test_get_docket_booking_choices_warehousing_is_vas_order(self):
		"""Warehousing Linked Service is creatable as VAS Order, not Inbound Order."""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			DOCKET_CREATABLE_JOB_TYPES,
			get_docket_booking_choices,
		)

		self.assertIn("VAS Order", DOCKET_CREATABLE_JOB_TYPES)
		self.assertNotIn("Inbound Order", DOCKET_CREATABLE_JOB_TYPES)

		exhibit = self._minimal_exhibit("Docket Choices VAS")
		dk = self._minimal_docket(exhibit.name)
		ls_name = None
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Warehousing"
			ls.job_type = "VAS Order"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			ls_name = ls.name

			msg = get_docket_booking_choices(dk.name)
			choices = msg.get("choices") or []
			vas = [c for c in choices if c.get("job_type") == "VAS Order"]
			self.assertTrue(vas)
			self.assertEqual(vas[0].get("service_type"), "Warehousing")
			# Eligibility may block create without a Sales Quote — job type must still be VAS.
			inbound = [c for c in choices if c.get("job_type") == "Inbound Order"]
			self.assertFalse(inbound)
			with patch(
				"logistics.utils.internal_job_creation_eligibility.evaluate_internal_job_creation_eligibility",
				return_value={"eligible": True, "message": None},
			):
				msg2 = get_docket_booking_choices(dk.name)
			vas2 = [c for c in (msg2.get("choices") or []) if c.get("job_type") == "VAS Order"]
			self.assertTrue(vas2)
			self.assertTrue(vas2[0].get("creatable"))
		finally:
			if ls_name and frappe.db.exists(linked_service_doctype(), ls_name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_create_sea_booking_from_docket_persists_job_no(self):
		"""Docket Create → Sea Booking must write Job No onto the Docket Linked Service."""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			create_booking_or_order_from_docket,
		)
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		if not frappe.db.exists("DocType", "Sea Booking"):
			self.skipTest("Sea Booking not installed")

		exhibit = self._minimal_exhibit("Docket Create SB Persist")
		dk = self._minimal_docket(exhibit.name)
		self._seed_docket_accounts(dk.name)
		order_name = None
		ls_name = None
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Sea"
			ls.job_type = "Sea Booking"
			port = frappe.db.get_value("UNLOCO", {}, "name") or frappe.db.get_value("Port", {}, "name")
			if port and ls.meta.has_field("origin_port"):
				ls.origin_port = port
				ls.destination_port = port
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			ls_name = ls.name

			stub_payload = [{"service_type": "Sea", "job_type": "Sea Booking"}]
			orig_insert = frappe.model.document.Document.insert
			with patch(
				"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible"
			), patch.object(
				frappe.model.document.Document,
				"insert",
				self._insert_ignore_mandatory(orig_insert),
			):
				result = create_booking_or_order_from_docket(
					docket=dk.name,
					job_type="Sea Booking",
					internal_job_idx=1,
					linked_services=stub_payload,
				)
			order_name = result.get("sea_booking")
			self.assertTrue(order_name)

			ls.reload()
			self.assertEqual((ls.job_type or "").strip(), "Sea Booking")
			self.assertEqual((ls.job_no or "").strip(), order_name)

			view = build_linked_services_view_for_booking("Docket", dk.name)
			self.assertEqual(len(view), 1)
			self.assertEqual((view[0].get("job_no") or "").strip(), order_name)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			if order_name and frappe.db.exists("Sea Booking", order_name):
				frappe.delete_doc("Sea Booking", order_name, force=True, ignore_permissions=True)
			if ls_name and frappe.db.exists(linked_service_doctype(), ls_name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_create_declaration_order_from_docket_persists_job_no(self):
		"""Docket Create → Declaration Order must write Job No onto the Docket Linked Service."""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			create_booking_or_order_from_docket,
		)
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		if not frappe.db.exists("DocType", "Declaration Order"):
			self.skipTest("Declaration Order not installed")

		exhibit = self._minimal_exhibit("Docket Create DO Persist")
		dk = self._minimal_docket(exhibit.name)
		self._seed_docket_accounts(dk.name)
		order_name = None
		ls_name = None
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Customs"
			ls.job_type = "Declaration Order"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			ls_name = ls.name

			stub_payload = [{"service_type": "Customs", "job_type": "Declaration Order"}]
			orig_insert = frappe.model.document.Document.insert
			with patch(
				"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible"
			), patch.object(
				frappe.model.document.Document,
				"insert",
				self._insert_ignore_mandatory(orig_insert),
			):
				result = create_booking_or_order_from_docket(
					docket=dk.name,
					job_type="Declaration Order",
					internal_job_idx=1,
					linked_services=stub_payload,
				)
			order_name = result.get("declaration_order")
			self.assertTrue(order_name)

			ls.reload()
			self.assertEqual((ls.job_type or "").strip(), "Declaration Order")
			self.assertEqual((ls.job_no or "").strip(), order_name)

			view = build_linked_services_view_for_booking("Docket", dk.name)
			self.assertEqual(len(view), 1)
			self.assertEqual((view[0].get("job_no") or "").strip(), order_name)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			if order_name and frappe.db.exists("Declaration Order", order_name):
				frappe.delete_doc(
					"Declaration Order", order_name, force=True, ignore_permissions=True
				)
			if ls_name and frappe.db.exists(linked_service_doctype(), ls_name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_create_vas_order_from_docket_persists_job_no(self):
		"""Docket Create → VAS Order must write Job No onto the Docket Linked Service."""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			create_booking_or_order_from_docket,
		)
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		if not frappe.db.exists("DocType", "VAS Order"):
			self.skipTest("VAS Order not installed")

		exhibit = self._minimal_exhibit("Docket Create VAS Persist")
		dk = self._minimal_docket(exhibit.name)
		self._seed_docket_accounts(dk.name)
		order_name = None
		ls_name = None
		fake_contract = f"WC-TEST-{frappe.generate_hash(length=6)}"
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Warehousing"
			ls.job_type = "VAS Order"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			ls_name = ls.name

			stub_payload = [{"service_type": "Warehousing", "job_type": "VAS Order"}]
			orig_insert = frappe.model.document.Document.insert

			def _insert_ignore_links(self, *args, **kwargs):
				self.flags.ignore_mandatory = True
				self.flags.ignore_links = True
				kwargs.setdefault("ignore_mandatory", True)
				kwargs.setdefault("ignore_links", True)
				return orig_insert(self, *args, **kwargs)

			with patch(
				"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible"
			), patch(
				"logistics.utils.module_integration._get_customer_warehouse_contract",
				return_value=fake_contract,
			), patch(
				"logistics.utils.module_integration._get_or_create_cross_dock_vas_order_type",
				return_value="CROSS-DOCK",
			), patch(
				"logistics.utils.module_integration._fill_vas_order_accounts_from_source",
			), patch.object(
				frappe.model.document.Document,
				"insert",
				_insert_ignore_links,
			):
				result = create_booking_or_order_from_docket(
					docket=dk.name,
					job_type="VAS Order",
					internal_job_idx=1,
					linked_services=stub_payload,
				)
			order_name = result.get("vas_order")
			self.assertTrue(order_name)

			ls.reload()
			self.assertEqual((ls.job_type or "").strip(), "VAS Order")
			self.assertEqual((ls.job_no or "").strip(), order_name)

			view = build_linked_services_view_for_booking("Docket", dk.name)
			self.assertEqual(len(view), 1)
			self.assertEqual((view[0].get("job_no") or "").strip(), order_name)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			if order_name and frappe.db.exists("VAS Order", order_name):
				frappe.delete_doc("VAS Order", order_name, force=True, ignore_permissions=True)
			if ls_name and frappe.db.exists(linked_service_doctype(), ls_name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_create_transport_preserves_existing_sea_job_no(self):
		"""Creating Transport Order must not clear a previously stamped Sea Booking Job No.

		Reproduces the desk bug: multi-row linked_services payload (Sea with linked_service +
		blank job_no, Transport pending) was applied during TRO insert and reparented/wiped
		the Docket-owned Sea Linked Service.
		"""
		from unittest.mock import patch

		from logistics.mice.doctype.docket.docket_booking_creation import (
			create_booking_or_order_from_docket,
		)
		from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking

		if not frappe.db.exists("DocType", "Transport Order"):
			self.skipTest("Transport Order not installed")

		exhibit = self._minimal_exhibit("Docket Sea Then TRO")
		dk = self._minimal_docket(exhibit.name)
		self._seed_docket_accounts(dk.name)
		sea_job_no = f"SB-TEST-{frappe.generate_hash(length=8)}"
		order_name = None
		sea_ls_name = None
		tro_ls_name = None
		try:
			sea_ls = frappe.new_doc(linked_service_doctype())
			sea_ls.parent_booking_type = "Docket"
			sea_ls.parent_booking_name = dk.name
			sea_ls.service_type = "Sea"
			sea_ls.job_type = "Sea Booking"
			sea_ls.job_no = sea_job_no
			sea_ls.flags.ignore_mandatory = True
			sea_ls.insert(ignore_permissions=True)
			sea_ls_name = sea_ls.name

			tro_ls = frappe.new_doc(linked_service_doctype())
			tro_ls.parent_booking_type = "Docket"
			tro_ls.parent_booking_name = dk.name
			tro_ls.service_type = "Transport"
			tro_ls.job_type = "Transport Order"
			tro_ls.flags.ignore_mandatory = True
			tro_ls.insert(ignore_permissions=True)
			tro_ls_name = tro_ls.name

			# Stale desk payload: Sea row still points at Docket LS but Job No is blank.
			stub_payload = [
				{
					"linked_service": sea_ls_name,
					"service_type": "Sea",
					"job_type": "Sea Booking",
					"job_no": "",
				},
				{
					"linked_service": tro_ls_name,
					"service_type": "Transport",
					"job_type": "Transport Order",
				},
			]
			orig_insert = frappe.model.document.Document.insert
			with patch(
				"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible"
			), patch.object(
				frappe.model.document.Document,
				"insert",
				self._insert_ignore_mandatory(orig_insert),
			):
				result = create_booking_or_order_from_docket(
					docket=dk.name,
					job_type="Transport Order",
					internal_job_idx=2,
					linked_services=stub_payload,
				)
			order_name = result.get("transport_order")
			self.assertTrue(order_name)

			sea_ls.reload()
			self.assertEqual((sea_ls.job_no or "").strip(), sea_job_no)
			self.assertEqual((sea_ls.parent_booking_type or "").strip(), "Docket")
			self.assertEqual((sea_ls.parent_booking_name or "").strip(), dk.name)

			tro_ls.reload()
			self.assertEqual((tro_ls.job_no or "").strip(), order_name)
			self.assertEqual((tro_ls.parent_booking_type or "").strip(), "Docket")
			self.assertEqual((tro_ls.parent_booking_name or "").strip(), dk.name)

			view = build_linked_services_view_for_booking("Docket", dk.name)
			by_type = {
				(r.get("job_type") or "").strip(): (r.get("job_no") or "").strip() for r in view
			}
			self.assertEqual(by_type.get("Sea Booking"), sea_job_no)
			self.assertEqual(by_type.get("Transport Order"), order_name)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			if order_name and frappe.db.exists("Transport Order", order_name):
				frappe.delete_doc("Transport Order", order_name, force=True, ignore_permissions=True)
			for name in (sea_ls_name, tro_ls_name):
				if name and frappe.db.exists(linked_service_doctype(), name):
					frappe.delete_doc(
						linked_service_doctype(), name, force=True, ignore_permissions=True
					)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)
