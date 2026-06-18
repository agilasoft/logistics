# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import MagicMock

from logistics.utils.charge_service_type import (
	filter_operational_doc_charges_for_internal_job_row,
	operational_booking_charge_service_type_label,
)


class TestOperationalChargeServiceType(unittest.TestCase):
	def test_mice_maps_to_operational_child_label(self):
		self.assertEqual(operational_booking_charge_service_type_label("MICE"), "MICE")
		self.assertEqual(operational_booking_charge_service_type_label("Exhibits"), "MICE")
		self.assertEqual(operational_booking_charge_service_type_label("mice"), "MICE")

	def test_filter_operational_doc_charges_for_internal_job_row(self):
		parent = MagicMock()
		parent.doctype = "Declaration Order"
		customs = MagicMock(service_type="Customs")
		mice = MagicMock(service_type="MICE")
		parent.charges = [customs, mice]
		row = MagicMock(service_type="Customs")

		filter_operational_doc_charges_for_internal_job_row(parent, row)

		parent.set.assert_called_once()
		kept = parent.set.call_args[0][1]
		self.assertEqual(len(kept), 1)
		self.assertEqual(customs.service_type, "Customs")
		self.assertEqual(mice.service_type, "MICE")
