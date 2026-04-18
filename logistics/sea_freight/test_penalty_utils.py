# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from frappe.tests import UnitTestCase
from frappe.utils import getdate

from logistics.sea_freight import penalty_utils


class _Settings:
	def __init__(self, default_ft=7, det_r=10, dem_r=20):
		self.default_free_time_days = default_ft
		self.detention_rate_per_day = det_r
		self.demurrage_rate_per_day = dem_r


class UnitTestPenaltyUtils(UnitTestCase):
	def test_effective_free_time_defaults(self):
		s = _Settings()
		self.assertEqual(penalty_utils.effective_free_time_days(None, s), 7)

		class C:
			free_time_days = None

		self.assertEqual(penalty_utils.effective_free_time_days(C(), s), 7)

		class C2:
			free_time_days = 14

		self.assertEqual(penalty_utils.effective_free_time_days(C2(), s), 14)

	def test_detention_reference_prefers_ata_over_eta_when_no_milestone(self):
		class M:
			pass

		ship = M()
		ship.milestones = []
		ship.ata = getdate("2026-02-10")
		ship.eta = getdate("2026-02-01")
		self.assertEqual(penalty_utils.get_detention_reference_date(ship), getdate("2026-02-10"))

	def test_detention_reference_sf_discharged_before_ata(self):
		class Row:
			milestone = "SF-DISCHARGED"
			actual_end = "2026-03-01"

		class M:
			pass

		ship = M()
		ship.milestones = [Row()]
		ship.ata = getdate("2026-02-10")
		self.assertEqual(penalty_utils.get_detention_reference_date(ship), getdate("2026-03-01"))

	def test_compute_penalty_days_detention_only(self):
		today = getdate("2026-01-20")
		ref = getdate("2026-01-01")
		d_det, d_dem = penalty_utils.compute_penalty_days(ref, None, today, 7)
		# 19 days since ref, 7 free -> 12 detention
		self.assertEqual(d_det, 12)
		self.assertEqual(d_dem, 0)

	def test_estimated_penalty_amount_for_days(self):
		s = _Settings(default_ft=7, det_r=10, dem_r=5)
		amt = penalty_utils.estimated_penalty_amount_for_days(2, 4, s)
		self.assertEqual(amt, 2 * 10 + 4 * 5)
