# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Linked Service Warehousing maps to VAS Order (cross-dock / in-transit), not storage Inbound."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from logistics.utils.charge_service_type import (
	default_job_type_for_internal_job_service_type,
	effective_internal_job_detail_job_type,
)
from logistics.utils.internal_job_from_source import CREATABLE_INTERNAL_JOB_TYPES


class TestLinkedWarehousingVasOrder(unittest.TestCase):
	def test_default_job_type_is_vas_order(self):
		self.assertEqual(default_job_type_for_internal_job_service_type("Warehousing"), "VAS Order")
		self.assertEqual(default_job_type_for_internal_job_service_type("warehousing"), "VAS Order")

	def test_effective_job_type_prefers_vas_for_open_warehousing_rows(self):
		row = SimpleNamespace(service_type="Warehousing", job_type="Inbound Order", job_no="")
		self.assertEqual(effective_internal_job_detail_job_type(row), "VAS Order")

		row_vas = SimpleNamespace(service_type="Warehousing", job_type="VAS Order", job_no="")
		self.assertEqual(effective_internal_job_detail_job_type(row_vas), "VAS Order")

	def test_legacy_storage_order_kept_when_already_linked(self):
		row = SimpleNamespace(
			service_type="Warehousing", job_type="Inbound Order", job_no="INB-0001"
		)
		self.assertEqual(effective_internal_job_detail_job_type(row), "Inbound Order")

	def test_vas_order_is_creatable_internal_job_type(self):
		self.assertIn("VAS Order", CREATABLE_INTERNAL_JOB_TYPES)
		self.assertNotIn("Inbound Order", CREATABLE_INTERNAL_JOB_TYPES)
