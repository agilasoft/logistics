# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, today

from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_branch,
	create_test_consignee,
	create_test_cost_center,
	create_test_profit_center,
	create_test_shipper,
	create_test_unloco,
)
from logistics.utils.consolidation_plan import get_strict_matching_sea_shipment_names


def _ensure_sea_freight_settings_defaults(company, cost_center, profit_center):
	if frappe.db.exists("Sea Freight Settings", company):
		ss = frappe.get_doc("Sea Freight Settings", company)
	else:
		ss = frappe.get_doc({"doctype": "Sea Freight Settings", "company": company})
		ss.flags.ignore_validate = True
		ss.insert(ignore_permissions=True)
	ss.default_cost_center = cost_center
	ss.default_profit_center = profit_center
	ss.save(ignore_permissions=True)


def _ensure_shipping_line(code="TEST-SLINE"):
	if frappe.db.exists("Shipping Line", code):
		return code
	sl = frappe.get_doc(
		{
			"doctype": "Shipping Line",
			"code": code,
			"shipping_line_name": "Test Shipping Line",
			"is_active": 1,
			"scac": "TST",
		}
	)
	sl.insert(ignore_permissions=True)
	return code


class TestSeaConsolidationPlanning(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Port")
		create_test_unloco("USJFK", "New York", "JFK", "US", "Port")
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		_ensure_sea_freight_settings_defaults(self.company, self.cost_center, self.profit_center)
		self.shipping_line = _ensure_shipping_line()

	def tearDown(self):
		frappe.db.rollback()

	def _make_sea_shipment(self):
		sh = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"weight": 20,
				"volume": 0.2,
			}
		)
		sh.insert()
		return sh.name

	def _make_sea_shipment_for_fetch(
		self,
		etd_date,
		*,
		vessel="MV TestVessel",
		voyage="VY001",
		shipping_line=None,
	):
		sl = shipping_line or self.shipping_line
		sfx = frappe.generate_hash(length=8)
		mb = frappe.get_doc(
			{
				"doctype": "Master Bill",
				"master_bl": "TEST-MBL-FETCH-{0}".format(sfx),
				"master_type": "Direct",
				"shipping_line": sl,
				"vessel": vessel,
				"voyage_no": voyage,
			}
		)
		mb.insert(ignore_permissions=True)
		sh = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"weight": 20,
				"volume": 0.2,
				"shipping_line": sl,
				"master_bill": mb.name,
				"etd": etd_date,
			}
		)
		sh.insert()
		return sh.name

	def _make_sea_consolidation(self, **kwargs):
		etd = kwargs.pop("etd", now_datetime())
		eta = kwargs.pop("eta", add_to_date(etd, days=5))
		doc = frappe.get_doc(
			{
				"doctype": "Sea Consolidation",
				"naming_series": "SC-{MM}-{YYYY}-{####}",
				"consolidation_date": today(),
				"consolidation_type": "Direct Consolidation",
				"status": "Draft",
				"company": self.company,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"etd": etd,
				"eta": eta,
				"shipping_line": self.shipping_line,
				"vessel_name": "TBA",
				"voyage_number": "TBA",
				**kwargs,
			}
		)
		doc.insert()
		return doc

	def test_submit_planning_then_packages_validate(self):
		sh = self._make_sea_shipment()
		consol = self._make_sea_consolidation()
		consol.append("consolidation_planning_lines", {"sea_shipment": sh})
		consol.save()
		consol.reload()
		consol.submit_sea_planning()
		consol.reload()
		self.assertEqual(consol.sea_planning_status, "Submitted")

	def test_house_bill_prefix_assigns_house_bl_on_planning_shipments(self):
		sh1 = self._make_sea_shipment()
		sh2 = self._make_sea_shipment()
		consol = self._make_sea_consolidation()
		consol.house_bill_prefix = "TSTHBL"
		consol.append("consolidation_planning_lines", {"sea_shipment": sh1})
		consol.append("consolidation_planning_lines", {"sea_shipment": sh2})
		consol.save()
		h1 = frappe.db.get_value("Sea Shipment", sh1, "house_bl")
		h2 = frappe.db.get_value("Sea Shipment", sh2, "house_bl")
		self.assertTrue(h1 and h1.startswith("TSTHBL-"))
		self.assertTrue(h2 and h2.startswith("TSTHBL-"))
		self.assertNotEqual(h1, h2)

	def test_house_bill_prefix_does_not_overwrite_existing_house_bl(self):
		sh1 = self._make_sea_shipment()
		sh2 = self._make_sea_shipment()
		existing = "MANUAL-HBL-XYZ-001"
		frappe.db.set_value("Sea Shipment", sh1, "house_bl", existing)
		consol = self._make_sea_consolidation()
		consol.house_bill_prefix = "NEWPRE"
		consol.append("consolidation_planning_lines", {"sea_shipment": sh1})
		consol.append("consolidation_planning_lines", {"sea_shipment": sh2})
		consol.save()
		self.assertEqual(frappe.db.get_value("Sea Shipment", sh1, "house_bl"), existing)
		h2 = frappe.db.get_value("Sea Shipment", sh2, "house_bl")
		self.assertTrue(h2 and h2.startswith("NEWPRE-"))

	def test_cannot_submit_consolidation_with_only_one_sea_shipment(self):
		sh = self._make_sea_shipment()
		consol = self._make_sea_consolidation()
		td = now_datetime()
		consol.append(
			"consolidation_routes",
			{
				"route_type": "Direct",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"shipping_line": self.shipping_line,
				"vessel_name": "MV RouteLeg",
				"voyage_number": "RV-1",
				"etd": td,
				"eta": add_to_date(td, days=5),
			},
		)
		consol.append("consolidation_planning_lines", {"sea_shipment": sh})
		sh_doc = frappe.get_doc("Sea Shipment", sh)
		consol.append(
			"consolidation_packages",
			{
				"package_reference": "{0}-TESTPKG".format(sh),
				"sea_shipment": sh,
				"shipper": sh_doc.shipper,
				"consignee": sh_doc.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": 20,
				"package_volume": 0.2,
			},
		)
		consol.save()
		consol.reload()
		consol.submit_sea_planning()
		consol.reload()
		with self.assertRaises(ValidationError) as ctx:
			consol.submit()
		self.assertIn("two", str(ctx.exception).lower())

	def test_cancel_planning_submit_retains_planning_lines(self):
		sh = self._make_sea_shipment()
		consol = self._make_sea_consolidation()
		consol.append("consolidation_planning_lines", {"sea_shipment": sh})
		consol.save()
		consol.reload()
		consol.submit_sea_planning()
		consol.reload()
		self.assertEqual(len(consol.consolidation_planning_lines), 1)
		consol.cancel_sea_planning_submit()
		consol.reload()
		self.assertEqual(consol.sea_planning_status, "Draft")
		self.assertEqual(len(consol.consolidation_planning_lines or []), 1)
		self.assertEqual(consol.consolidation_planning_lines[0].sea_shipment, sh)

	def test_cancel_planning_succeeds_when_attached_rows_stale_without_cargo(self):
		"""Packages were removed but hidden attached_sea_shipments rows remained (sync skipped)."""
		sh = self._make_sea_shipment()
		consol = self._make_sea_consolidation()
		consol.append("consolidation_planning_lines", {"sea_shipment": sh})
		sh_doc = frappe.get_doc("Sea Shipment", sh)
		consol.append(
			"consolidation_packages",
			{
				"package_reference": "{0}-STALEATT".format(sh),
				"sea_shipment": sh,
				"shipper": sh_doc.shipper,
				"consignee": sh_doc.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": 20,
				"package_volume": 0.2,
			},
		)
		consol.save()
		consol.reload()
		consol.submit_sea_planning()
		consol.reload()
		self.assertTrue(
			frappe.db.exists("Sea Consolidation Shipments", {"parent": consol.name, "sea_shipment": sh})
		)
		frappe.db.sql("DELETE FROM `tabSea Consolidation Packages` WHERE parent = %s", (consol.name,))
		consol = frappe.get_doc("Sea Consolidation", consol.name)
		self.assertFalse(consol.get("consolidation_packages"))
		self.assertTrue(consol.get("attached_sea_shipments"))
		consol.cancel_sea_planning_submit()
		consol.reload()
		self.assertEqual(consol.sea_planning_status, "Draft")

	def test_filtered_match_destination_and_company_only(self):
		etd_date = add_days(today(), 22)
		create_test_unloco("USBOS", "Boston", "BOS", "US", "Port")
		to_jfk = self._make_sea_shipment_for_fetch(etd_date, vessel="MV Beta", voyage="V-200")
		via_bos = self._make_sea_shipment_standalone(
			origin="USBOS",
			destination="USJFK",
			etd_date=etd_date,
			vessel="MV Gamma",
			voyage="V-300",
		)
		other_dest = self._make_sea_shipment_standalone(
			origin="USLAX",
			destination="USLAX",
			etd_date=etd_date,
			vessel="MV Other",
			voyage="V-999",
		)
		plan = {"company": self.company, "destination_port": "USJFK"}
		names = get_strict_matching_sea_shipment_names(plan)
		self.assertIn(to_jfk, names)
		self.assertIn(via_bos, names)
		self.assertNotIn(other_dest, names)

	def _make_sea_shipment_standalone(
		self,
		*,
		origin,
		destination,
		etd_date,
		vessel="MV Solo",
		voyage="V-SOLO",
		shipping_line=None,
	):
		sl = shipping_line or self.shipping_line
		sfx = frappe.generate_hash(length=8)
		mb = frappe.get_doc(
			{
				"doctype": "Master Bill",
				"master_bl": "TEST-MBL-SOLO-{0}".format(sfx),
				"master_type": "Direct",
				"shipping_line": sl,
				"vessel": vessel,
				"voyage_no": voyage,
			}
		)
		mb.insert(ignore_permissions=True)
		sh = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": origin,
				"destination_port": destination,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"weight": 20,
				"volume": 0.2,
				"shipping_line": sl,
				"master_bill": mb.name,
				"etd": etd_date,
			}
		)
		sh.insert()
		return sh.name

	def test_strict_match_excludes_submitted_sea_shipment(self):
		etd_date = add_days(today(), 21)
		target_etd = get_datetime(f"{etd_date} 11:00:00")
		target_eta = add_to_date(target_etd, days=5)
		sh_name = self._make_sea_shipment_for_fetch(etd_date, vessel="MV Alpha", voyage="V-100")
		frappe.db.set_value("Sea Shipment", sh_name, "job_status", "Submitted")
		plan = {
			"company": self.company,
			"branch": self.branch,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"target_etd": target_etd,
			"shipping_line": self.shipping_line,
			"vessel_name": "MV Alpha",
			"voyage_number": "V-100",
		}
		names = get_strict_matching_sea_shipment_names(plan)
		self.assertNotIn(sh_name, names)

	def test_fetch_matching_sea_shipments_strict(self):
		etd_date = add_days(today(), 21)
		target_etd = get_datetime(f"{etd_date} 11:00:00")
		target_eta = add_to_date(target_etd, days=5)
		good = self._make_sea_shipment_for_fetch(etd_date, vessel="MV Alpha", voyage="V-100")
		self._make_sea_shipment_for_fetch(etd_date, vessel="MV Alpha", voyage="V-999")
		consol = self._make_sea_consolidation(etd=target_etd, eta=target_eta)
		consol.db_set("vessel_name", "MV Alpha")
		consol.db_set("voyage_number", "V-100")
		consol.reload()
		out = consol.fetch_matching_sea_shipments()
		self.assertIn(good, out["added"])
		self.assertEqual(len(out["added"]), 1)
		consol.reload()
		pkg_for = [p for p in (consol.consolidation_packages or []) if p.sea_shipment == good]
		self.assertEqual(len(pkg_for), 1)
		out2 = consol.fetch_matching_sea_shipments()
		self.assertEqual(out2["added"], [])
		self.assertIn(good, out2["already_present"])
		consol.reload()
		pkg_for2 = [p for p in (consol.consolidation_packages or []) if p.sea_shipment == good]
		self.assertEqual(len(pkg_for2), len(pkg_for))

	def test_fetch_matching_populates_one_consolidation_package_per_sea_freight_line(self):
		etd_date = add_days(today(), 23)
		target_etd = get_datetime(f"{etd_date} 11:00:00")
		target_eta = add_to_date(target_etd, days=5)
		sfx = frappe.generate_hash(length=6)
		good = self._make_sea_shipment_for_fetch(
			etd_date, vessel="MV PkgLines", voyage="PL-{0}".format(sfx)
		)
		sh = frappe.get_doc("Sea Shipment", good)
		sh.append(
			"packages",
			{
				"no_of_packs": 2,
				"weight": 10,
				"volume": 0.05,
				"reference_no": "SRF-{0}-A".format(sfx),
			},
		)
		sh.append(
			"packages",
			{
				"no_of_packs": 1,
				"weight": 10,
				"volume": 0.05,
				"reference_no": "SRF-{0}-B".format(sfx),
			},
		)
		sh.save()
		consol = self._make_sea_consolidation(etd=target_etd, eta=target_eta)
		consol.db_set("vessel_name", "MV PkgLines")
		consol.db_set("voyage_number", "PL-{0}".format(sfx))
		consol.reload()
		consol.fetch_matching_sea_shipments()
		consol.reload()
		pkg_for = [p for p in (consol.consolidation_packages or []) if p.sea_shipment == good]
		self.assertEqual(len(pkg_for), 2)
		refs = {p.package_reference for p in pkg_for}
		self.assertIn("SRF-{0}-A".format(sfx), refs)
		self.assertIn("SRF-{0}-B".format(sfx), refs)

	def test_apply_selected_sea_shipments_to_planning_populates_packages(self):
		etd_date = add_days(today(), 24)
		target_etd = get_datetime(f"{etd_date} 11:00:00")
		target_eta = add_to_date(target_etd, days=5)
		sfx = frappe.generate_hash(length=6)
		good = self._make_sea_shipment_for_fetch(
			etd_date, vessel="MV ApplySel", voyage="AS-{0}".format(sfx)
		)
		consol = self._make_sea_consolidation(etd=target_etd, eta=target_eta)
		consol.db_set("vessel_name", "MV ApplySel")
		consol.db_set("voyage_number", "AS-{0}".format(sfx))
		consol.reload()
		consol.apply_selected_sea_shipments_to_planning([good])
		consol.reload()
		self.assertTrue(
			any(
				getattr(r, "sea_shipment", None) == good
				for r in (consol.consolidation_planning_lines or [])
			)
		)
		pkg_for = [p for p in (consol.consolidation_packages or []) if p.sea_shipment == good]
		self.assertEqual(len(pkg_for), 1)
