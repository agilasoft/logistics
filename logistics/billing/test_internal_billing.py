# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

from __future__ import unicode_literals

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.billing.internal_billing import (
    _append_revenue_transfer_rows,
    _internal_billing_jv_user_remark,
    create_internal_billing_journal_entries_for_quote,
)
from logistics.utils.item_accounts import (
    get_expense_account_for_item,
    get_income_account_for_item,
    get_item_accounts_for_internal_billing,
)

_REAL_GET_DOC = frappe.get_doc


class TestItemAccounts(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = frappe.db.get_single_value("Global Defaults", "default_company")
        if not cls.company:
            cls.company = frappe.get_all("Company", limit=1)[0].name
        cls._ensure_account("IB Test Expense", "Expense", "Expense Account")
        cls._ensure_account("IB Test Income", "Income", "Income Account")
        cls._ensure_test_item()

    @classmethod
    def _ensure_account(cls, account_name, root_type, account_type):
        if frappe.db.exists("Account", {"account_name": account_name, "company": cls.company}):
            return frappe.db.get_value(
                "Account", {"account_name": account_name, "company": cls.company}, "name"
            )
        parent = frappe.db.get_value(
            "Account",
            {"company": cls.company, "root_type": root_type, "is_group": 1},
            "name",
        )
        doc = frappe.new_doc("Account")
        doc.account_name = account_name
        doc.company = cls.company
        doc.root_type = root_type
        doc.account_type = account_type
        doc.parent_account = parent
        doc.insert(ignore_permissions=True)
        return doc.name

    @classmethod
    def _ensure_test_item(cls):
        cls.item_code = "IB-Test-Charge-Item"
        expense = frappe.db.get_value(
            "Account", {"account_name": "IB Test Expense", "company": cls.company}, "name"
        )
        income = frappe.db.get_value(
            "Account", {"account_name": "IB Test Income", "company": cls.company}, "name"
        )
        if frappe.db.exists("Item", cls.item_code):
            item = frappe.get_doc("Item", cls.item_code)
            item.item_defaults = []
        else:
            item = frappe.new_doc("Item")
            item.item_code = cls.item_code
            item.item_name = cls.item_code
            item.item_group = "All Item Groups"
            item.stock_uom = "Nos"
            item.is_stock_item = 0
        item.append(
            "item_defaults",
            {
                "company": cls.company,
                "expense_account": expense,
                "income_account": income,
            },
        )
        item.save(ignore_permissions=True)
        cls.expense_account = expense
        cls.income_account = income

    def test_item_default_accounts_resolved(self):
        self.assertEqual(
            get_expense_account_for_item(self.item_code, self.company),
            self.expense_account,
        )
        self.assertEqual(
            get_income_account_for_item(self.item_code, self.company),
            self.income_account,
        )
        exp, inc = get_item_accounts_for_internal_billing(self.item_code, self.company)
        self.assertEqual(exp, self.expense_account)
        self.assertEqual(inc, self.income_account)

    def test_missing_item_accounts_throw(self):
        with patch(
            "logistics.utils.item_accounts.get_expense_account_for_item",
            return_value=None,
        ):
            with patch(
                "logistics.utils.item_accounts.get_income_account_for_item",
                return_value=None,
            ):
                with self.assertRaises(frappe.ValidationError):
                    get_item_accounts_for_internal_billing(self.item_code, self.company)


class TestRevenueTransferRows(FrappeTestCase):
    def test_append_rows_dr_main_cr_linked(self):
        main = SimpleNamespace(
            doctype="Transport Job",
            name="TJ-MAIN-01",
            cost_center="CC-Main",
            profit_center=None,
            job_number="JCN-MAIN",
        )
        linked = SimpleNamespace(
            doctype="Transport Job",
            name="TJ-LINK-01",
            cost_center="CC-Link",
            profit_center=None,
            job_number="JCN-LINK",
        )
        entries = []
        with patch(
            "logistics.billing.internal_billing.get_item_accounts_for_internal_billing",
            return_value=("Exp-ACC", "Inc-ACC"),
        ):
            _append_revenue_transfer_rows(
                entries,
                main,
                linked,
                150.0,
                "ITEM-001",
                "Test Co",
                je_row_has_jcn=True,
            )
        self.assertEqual(len(entries), 2)
        dr, cr = entries
        self.assertEqual(dr["account"], "Exp-ACC")
        self.assertEqual(flt(dr["debit_in_account_currency"]), 150.0)
        self.assertEqual(dr["job_number"], "JCN-MAIN")
        self.assertEqual(cr["account"], "Inc-ACC")
        self.assertEqual(flt(cr["credit_in_account_currency"]), 150.0)
        self.assertEqual(cr["job_number"], "JCN-LINK")


class TestCreateInternalBillingJV(TestItemAccounts):
    def setUp(self):
        self.quote_name = "SQ-IB-TEST-{0}".format(frappe.generate_hash(length=6))
        self.main_job = SimpleNamespace(
            doctype="Transport Job",
            name="TJ-IB-MAIN",
            company=self.company,
            cost_center=None,
            profit_center=None,
            job_number="JCN-IB-MAIN",
        )
        self.linked_job = SimpleNamespace(
            doctype="Transport Job",
            name="TJ-IB-LINK",
            company=self.company,
            cost_center=None,
            profit_center=None,
            job_number="JCN-IB-LINK",
        )
        self.splits = [{"revenue": 200.0, "cost": 50.0, "item_code": self.item_code}]

    def _quote_doc(self):
        return SimpleNamespace(
            name=self.quote_name,
            customer="Test Customer",
            routing_legs=[SimpleNamespace()],
            branch=None,
            cost_center=None,
        )

    def _mock_get_doc(self, *args, **kwargs):
        if args and isinstance(args[0], dict):
            return _REAL_GET_DOC(*args, **kwargs)
        doctype, name = args[0], args[1]
        if doctype == "Sales Quote":
            return self._quote_doc()
        if name == self.main_job.name:
            return self.main_job
        if name == self.linked_job.name:
            return self.linked_job
        return _REAL_GET_DOC(doctype, name)

    def tearDown(self):
        remark = _internal_billing_jv_user_remark(self.quote_name, None)
        for je in frappe.get_all("Journal Entry", filters={"user_remark": remark}, pluck="name"):
            doc = frappe.get_doc("Journal Entry", je)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Journal Entry", je, force=1)

    @patch(
        "logistics.invoice_integration.internal_billing_recognition_reversal.reverse_recognition_for_internal_billing_je"
    )
    @patch("logistics.billing.internal_billing.frappe.get_doc")
    @patch("logistics.billing.cross_module_billing.iter_internal_job_charge_splits")
    @patch("logistics.billing.cross_module_billing.get_all_billing_jobs_from_sales_quote")
    @patch(
        "logistics.pricing_center.doctype.sales_quote.sales_quote._resolve_main_job_for_sales_quote"
    )
    def test_creates_single_balanced_jv(
        self,
        mock_resolve_main,
        mock_all_jobs,
        mock_splits,
        mock_get_doc,
        _mock_reversal,
    ):
        mock_resolve_main.return_value = ("Transport Job", self.main_job.name)
        mock_all_jobs.return_value = [
            ("Transport Job", self.main_job.name),
            ("Transport Job", self.linked_job.name),
        ]
        mock_splits.return_value = self.splits
        mock_get_doc.side_effect = self._mock_get_doc

        original_exists = frappe.db.exists
        with patch.object(frappe.db, "exists") as mock_exists:

            def _exists(dt, name=None, **kwargs):
                if dt == "Sales Quote":
                    return True
                if dt == "Transport Job":
                    return True
                return original_exists(dt, name, **kwargs)

            mock_exists.side_effect = _exists
            with patch(
                "logistics.billing.cross_module_billing.resolve_internal_job_main_job",
                return_value=("Transport Job", self.main_job.name),
            ):
                with patch(
                    "logistics.billing.cross_module_billing.get_main_job_company",
                    return_value=self.company,
                ):
                    result = create_internal_billing_journal_entries_for_quote(
                        self.quote_name,
                        trigger_si=None,
                    )

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("created"), 1)
        je_name = result.get("journal_entry")
        self.assertTrue(je_name)
        je = frappe.get_doc("Journal Entry", je_name)
        self.assertEqual(je.docstatus, 1)
        self.assertEqual(len(je.accounts), 2)
        dr_rows = [r for r in je.accounts if flt(r.debit_in_account_currency) > 0]
        cr_rows = [r for r in je.accounts if flt(r.credit_in_account_currency) > 0]
        self.assertEqual(len(dr_rows), 1)
        self.assertEqual(len(cr_rows), 1)
        self.assertEqual(dr_rows[0].account, self.expense_account)
        self.assertEqual(cr_rows[0].account, self.income_account)
        if frappe.get_meta("Journal Entry Account").get_field("job_number"):
            self.assertEqual(dr_rows[0].job_number, self.main_job.job_number)
            self.assertEqual(cr_rows[0].job_number, self.linked_job.job_number)
        total_dr = sum(flt(r.debit_in_account_currency) for r in je.accounts)
        total_cr = sum(flt(r.credit_in_account_currency) for r in je.accounts)
        self.assertEqual(total_dr, total_cr)

    @patch(
        "logistics.invoice_integration.internal_billing_recognition_reversal.reverse_recognition_for_internal_billing_je"
    )
    @patch("logistics.billing.internal_billing.frappe.get_doc")
    @patch("logistics.billing.cross_module_billing.iter_internal_job_charge_splits")
    @patch("logistics.billing.cross_module_billing.get_all_billing_jobs_from_sales_quote")
    @patch(
        "logistics.pricing_center.doctype.sales_quote.sales_quote._resolve_main_job_for_sales_quote"
    )
    def test_idempotent_second_run(
        self,
        mock_resolve_main,
        mock_all_jobs,
        mock_splits,
        mock_get_doc,
        _mock_reversal,
    ):
        mock_resolve_main.return_value = ("Transport Job", self.main_job.name)
        mock_all_jobs.return_value = [("Transport Job", self.linked_job.name)]
        mock_splits.return_value = self.splits
        mock_get_doc.side_effect = self._mock_get_doc

        original_exists = frappe.db.exists
        with patch.object(frappe.db, "exists") as mock_exists:
            created_je = []

            def _exists(dt, name=None, **kwargs):
                if dt == "Sales Quote":
                    return True
                if dt == "Transport Job":
                    return True
                if (
                    dt == "Journal Entry"
                    and isinstance(name, dict)
                    and name.get("docstatus") == 1
                    and name.get("user_remark")
                ):
                    return bool(created_je)
                return original_exists(dt, name, **kwargs)

            mock_exists.side_effect = _exists
            with patch(
                "logistics.billing.cross_module_billing.resolve_internal_job_main_job",
                return_value=("Transport Job", self.main_job.name),
            ):
                with patch(
                    "logistics.billing.cross_module_billing.get_main_job_company",
                    return_value=self.company,
                ):
                    first = create_internal_billing_journal_entries_for_quote(self.quote_name)
                    created_je.append(first.get("journal_entry"))
                    second = create_internal_billing_journal_entries_for_quote(self.quote_name)

        self.assertEqual(first.get("created"), 1)
        self.assertEqual(second.get("created"), 0)

    def test_missing_item_code_returns_error(self):
        with patch.object(frappe.db, "exists", return_value=True):
            with patch("logistics.billing.internal_billing.frappe.get_doc") as mock_get_doc:
                mock_get_doc.side_effect = self._mock_get_doc
                with patch(
                    "logistics.pricing_center.doctype.sales_quote.sales_quote._resolve_main_job_for_sales_quote",
                    return_value=("Transport Job", self.main_job.name),
                ):
                    with patch(
                        "logistics.billing.cross_module_billing.get_all_billing_jobs_from_sales_quote",
                        return_value=[("Transport Job", self.linked_job.name)],
                    ):
                        with patch(
                            "logistics.billing.cross_module_billing.resolve_internal_job_main_job",
                            return_value=("Transport Job", self.main_job.name),
                        ):
                            with patch(
                                "logistics.billing.cross_module_billing.get_main_job_company",
                                return_value=self.company,
                            ):
                                with patch(
                                    "logistics.billing.cross_module_billing.iter_internal_job_charge_splits",
                                    return_value=[{"revenue": 100, "cost": 0, "item_code": None}],
                                ):
                                    result = create_internal_billing_journal_entries_for_quote(
                                        self.quote_name
                                    )
        self.assertFalse(result.get("success"))
        self.assertIn("item_code", result.get("message", "").lower())


class TestMainJobLinkedScopeBilling(TestItemAccounts):
    def setUp(self):
        self.quote_name = "SQ-IB-LINKED-{0}".format(frappe.generate_hash(length=6))
        self.ls_name = "LS-TEST-IB"
        self.main_job = SimpleNamespace(
            doctype="Sea Shipment",
            name="SF-IB-MAIN",
            company=self.company,
            cost_center=None,
            profit_center=None,
            job_number="JCN-SF-MAIN",
            charges=[
                SimpleNamespace(
                    doctype="Sea Shipment Charges",
                    charge_scope="Linked",
                    linked_service=self.ls_name,
                    charge_item=self.item_code,
                    actual_revenue=0,
                    selling_amount=0,
                    estimated_revenue=350.0,
                )
            ],
        )
        self.linked_job = SimpleNamespace(
            doctype="Air Shipment",
            name="ASP-IB-LINK",
            company=self.company,
            cost_center=None,
            profit_center=None,
            job_number="JCN-ASP-LINK",
        )

    def tearDown(self):
        remark = _internal_billing_jv_user_remark(self.quote_name, None)
        for je in frappe.get_all("Journal Entry", filters={"user_remark": remark}, pluck="name"):
            doc = frappe.get_doc("Journal Entry", je)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Journal Entry", je, force=1)

    @patch(
        "logistics.invoice_integration.internal_billing_recognition_reversal.reverse_recognition_for_internal_billing_je"
    )
    @patch("logistics.billing.internal_billing.frappe.get_doc")
    @patch("logistics.billing.cross_module_billing.get_all_billing_jobs_from_sales_quote")
    @patch(
        "logistics.pricing_center.doctype.sales_quote.sales_quote._resolve_main_job_for_sales_quote"
    )
    def test_main_job_linked_scope_charge_creates_jv(
        self,
        mock_resolve_main,
        mock_all_jobs,
        mock_get_doc,
        _mock_reversal,
    ):
        mock_resolve_main.return_value = ("Sea Shipment", self.main_job.name)
        mock_all_jobs.return_value = [("Sea Shipment", self.main_job.name)]

        def _get_doc(*args, **kwargs):
            if args and isinstance(args[0], dict):
                return _REAL_GET_DOC(*args, **kwargs)
            doctype, name = args[0], args[1]
            if doctype == "Sales Quote":
                return SimpleNamespace(
                    name=self.quote_name,
                    customer="Test Customer",
                    routing_legs=[SimpleNamespace()],
                    branch=None,
                    cost_center=None,
                )
            if name == self.main_job.name:
                return self.main_job
            if name == self.linked_job.name:
                return self.linked_job
            return _REAL_GET_DOC(doctype, name)

        mock_get_doc.side_effect = _get_doc

        original_exists = frappe.db.exists
        with patch.object(frappe.db, "exists") as mock_exists:

            def _exists(dt, name=None, **kwargs):
                if dt == "Sales Quote":
                    return True
                return original_exists(dt, name, **kwargs)

            mock_exists.side_effect = _exists
            with patch(
                "logistics.billing.cross_module_billing.resolve_operational_job_for_linked_service",
                return_value=("Air Shipment", self.linked_job.name),
            ):
                with patch(
                    "logistics.billing.cross_module_billing.iter_internal_job_charge_splits",
                    return_value=[],
                ):
                    result = create_internal_billing_journal_entries_for_quote(self.quote_name)

        self.assertTrue(result.get("success"))
        self.assertEqual(result.get("created"), 1)
        je = frappe.get_doc("Journal Entry", result.get("journal_entry"))
        self.assertEqual(len(je.accounts), 2)
        self.assertEqual(flt(je.accounts[0].debit_in_account_currency), 350.0)
