# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.sea_freight.container_row_metrics import (
	_aggregate_packages_for_container,
	compute_container_cargo_metrics,
	sync_container_cargo_from_packages,
	sync_sea_freight_container_child_rows,
)
from logistics.utils.container_validation import calculate_iso6346_check_digit, normalize_container_number


def _iso_container(serial6: str) -> str:
	base = "MSCU" + serial6
	return base + str(calculate_iso6346_check_digit(base + "0"))


class TestContainerRowMetrics(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _container_type_with_capacity(self, suffix: str):
		ct_name = frappe.db.get_value("Container Type", {"active": 1, "max_gross_weight": [">", 0]}, "name")
		if ct_name:
			return ct_name
		doc = frappe.get_doc(
			{
				"doctype": "Container Type",
				"code": "T-CRM-{0}".format(suffix),
				"description": "Test container type for cargo rollup",
				"active": 1,
				"max_gross_weight": 20000,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_aggregate_packages_splits_by_container(self):
		cn_a = _iso_container("111111")
		cn_b = _iso_container("222222")
		key_a = normalize_container_number(cn_a)
		key_b = normalize_container_number(cn_b)

		packages = [
			frappe._dict({"container": cn_a, "no_of_packs": 3, "weight": 10, "volume": 0.5}),
			frappe._dict({"container": cn_b, "no_of_packs": 2, "weight": 5, "volume": 0.25}),
			frappe._dict({"container": "", "no_of_packs": 99, "weight": 100, "volume": 9}),
		]

		pa, wa, va = _aggregate_packages_for_container(packages, key_a, company=None)
		pb, wb, vb = _aggregate_packages_for_container(packages, key_b, company=None)

		self.assertEqual(flt(pa), 3)
		self.assertEqual(flt(pb), 2)
		self.assertGreater(flt(wa), 0)
		self.assertGreater(flt(wb), 0)
		self.assertGreater(flt(va), 0)
		self.assertGreater(flt(vb), 0)

	def test_sync_container_cargo_from_packages_on_parent_doc(self):
		suffix = frappe.generate_hash(length=6)
		cn_a = _iso_container("333333")
		cn_b = _iso_container("444444")
		ct = self._container_type_with_capacity(suffix)

		parent = frappe._dict(
			{
				"company": frappe.db.get_single_value("Global Defaults", "default_company"),
				"packages": [
					frappe._dict(
						{
							"container": cn_a,
							"no_of_packs": 4,
							"weight": 100,
							"volume": 1.2,
						}
					),
					frappe._dict(
						{
							"container": cn_b,
							"no_of_packs": 1,
							"weight": 25,
							"volume": 0.3,
						}
					),
				],
				"containers": [
					frappe._dict({"container_no": cn_a, "type": ct}),
					frappe._dict({"container_no": cn_b, "type": ct}),
					frappe._dict({"container_no": _iso_container("555555"), "type": ct}),
				],
			}
		)

		sync_sea_freight_container_child_rows(parent)

		self.assertEqual(parent.containers[0].packages_in_container, 4)
		self.assertGreater(flt(parent.containers[0].weight_in_container), 0)
		self.assertGreater(flt(parent.containers[0].volume_in_container), 0)
		self.assertEqual(parent.containers[1].packages_in_container, 1)
		self.assertEqual(parent.containers[2].packages_in_container, 0)
		self.assertEqual(flt(parent.containers[2].weight_in_container), 0)
		self.assertGreater(flt(parent.containers[0].utilization_percentage), 0)

	def test_compute_container_cargo_metrics_api(self):
		cn = _iso_container("666666")
		parent_dict = {
			"company": frappe.db.get_single_value("Global Defaults", "default_company"),
			"packages": [
				{
					"idx": 1,
					"container": cn,
					"no_of_packs": 2,
					"weight": 50,
					"volume": 0.75,
				}
			],
			"containers": [
				{"idx": 1, "container_no": cn, "type": self._container_type_with_capacity("api")},
			],
		}
		result = compute_container_cargo_metrics(parent_dict)
		self.assertIn("container_cargo", result)
		self.assertEqual(len(result["container_cargo"]), 1)
		row = result["container_cargo"][0]
		self.assertEqual(row["packages_in_container"], 2)
		self.assertGreater(flt(row["weight_in_container"]), 0)
		self.assertGreater(flt(row["volume_in_container"]), 0)

	def test_package_container_normalized_match(self):
		"""Package container string matches container_no via ISO normalization."""
		cn = _iso_container("777777")
		# Lowercase / spaced variant on package line
		pkg_ref = cn.lower()
		key = normalize_container_number(cn)

		packages = [
			frappe._dict({"container": pkg_ref, "no_of_packs": 7, "weight": 14, "volume": 0.7}),
		]
		packs, weight, volume = _aggregate_packages_for_container(packages, key, company=None)
		self.assertEqual(flt(packs), 7)
		self.assertGreater(flt(weight), 0)
		self.assertGreater(flt(volume), 0)
