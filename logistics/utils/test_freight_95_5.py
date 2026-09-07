# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Tests for freight 95/5 split helpers."""

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from logistics.utils.freight_95_5 import freight_split_applies, split_freight_amounts


class TestFreight95Split(FrappeTestCase):
    def test_split_amounts_sum_to_total(self):
        a95, a5 = split_freight_amounts(1000.0, company=None)
        self.assertAlmostEqual(a95 + a5, 1000.0, places=2)

    @patch("logistics.utils.freight_95_5.category_allows_95_5")
    def test_freight_split_applies_only_when_all_set(self, allows):
        allows.return_value = True
        ok = SimpleNamespace(
            charge_category="Freight",
            apply_95_5_rule=1,
            taxable_freight_item="ITEM-TAX",
        )
        self.assertTrue(freight_split_applies(ok))

        no_rule = SimpleNamespace(
            charge_category="Freight",
            apply_95_5_rule=0,
            taxable_freight_item="ITEM-TAX",
        )
        self.assertFalse(freight_split_applies(no_rule))

        allows.return_value = False
        flag_off = SimpleNamespace(
            charge_category="Freight",
            apply_95_5_rule=1,
            taxable_freight_item="ITEM-TAX",
        )
        self.assertFalse(freight_split_applies(flag_off))

        allows.return_value = True
        other_cat = SimpleNamespace(
            charge_category="Other",
            apply_95_5_rule=1,
            taxable_freight_item="ITEM-TAX",
        )
        self.assertTrue(freight_split_applies(other_cat))
