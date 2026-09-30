"""Header address taken from Branch Registration Details."""

from __future__ import annotations

import unittest

from logistics.print_format.purchase_invoice.header_address import (
	header_address_from_registration,
)


ATN = "ALL TRANSPORT NETWORK, INC."
ASL = "ALL SYSTEMS LOGISTICS INC."


class TestHeaderAddressFromRegistration(unittest.TestCase):
	def test_subic_strips_company_name(self):
		registration = (
			"All Transport Network, Inc.Unit 1-3A Subic Creative Center Building, "
			"Manila Avenue Cor. Dewey Avenue, Central Business District, "
			"Subic Bay 2222 Freeport Zone, Zambales Philippines"
		)
		address = header_address_from_registration(registration, ATN)
		self.assertEqual(
			address,
			"Unit 1-3A Subic Creative Center Building, "
			"Manila Avenue Cor. Dewey Avenue, Central Business District, "
			"Subic Bay 2222 Freeport Zone, Zambales Philippines",
		)
		self.assertNotIn("All Transport Network", address)

	def test_blank_registration_returns_empty(self):
		self.assertEqual(header_address_from_registration("", ATN), "")
		self.assertEqual(header_address_from_registration(None, ATN), "")
		self.assertEqual(header_address_from_registration("   \n  ", ATN), "")

	def test_vat_only_line_is_removed(self):
		registration = (
			"1-3 Subic Creative Centre Bldg., Manila Avenue corner Dewey Avenue,\n"
			"Central Business District, Subic Bay Freeport Zone 2222\n"
			"VAT Re. TIN: 200-003-195-00000"
		)
		address = header_address_from_registration(registration, ASL)
		self.assertEqual(
			address,
			"1-3 Subic Creative Centre Bldg., Manila Avenue corner Dewey Avenue, "
			"Central Business District, Subic Bay Freeport Zone 2222",
		)
		self.assertNotIn("VAT", address)

	def test_prefix_less_registration_is_unchanged(self):
		registration = (
			"2nd floor Baronesa Place, Mc Arthur Highway, Dau, "
			"Mabalacat City, Pampanga Philippines 2010"
		)
		self.assertEqual(
			header_address_from_registration(registration, "PRIME ALTA HOLDINGS, INC."),
			registration,
		)

	def test_asl_prefix_ignores_punctuation(self):
		registration = (
			"All Systems Logistics, Inc.3 Sta. Agueda Avenue, Pascor Drive, "
			"Sto. Nino, 170 City of Paranaque, NCR Fourth District, Philippines"
		)
		address = header_address_from_registration(registration, ASL)
		self.assertTrue(address.startswith("3 Sta. Agueda Avenue"))
		self.assertNotIn("All Systems Logistics", address)
