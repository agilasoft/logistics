# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
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
				"mbl_shipping_line": sl,
				"mbl_vessel": vessel,
				"mbl_voyage_no": voyage,
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

	def test_cancel_planning_submit_clears_planning_lines(self):
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
		self.assertEqual(len(consol.consolidation_planning_lines or []), 0)

	def test_strict_match_excludes_submitted_sea_shipment(self):
		etd_date = add_days(today(), 21)
		target_etd = get_datetime(f"{etd_date} 11:00:00")
		target_eta = add_to_date(target_etd, days=5)
		sh_name = self._make_sea_shipment_for_fetch(etd_date, vessel="MV Alpha", voyage="V-100")
		sh = frappe.get_doc("Sea Shipment", sh_name)
		sh.submit()
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
		out2 = consol.fetch_matching_sea_shipments()
		self.assertEqual(out2["added"], [])
		self.assertIn(good, out2["already_present"])
