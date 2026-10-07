# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import pathlib
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.cancel_linked_docs import (
    cancel_all_linked_docs,
    get_submitted_linked_docs,
)
from logistics.invoice_integration.lifecycle import (
    INVOICE_CANCEL_PRESERVED_JOBS,
    extend_invoice_ignore_linked_doctypes,
    merge_invoice_cancel_ignore_doctypes,
)


class TestMergeInvoiceCancelIgnoreDoctypes(UnitTestCase):
    def test_sales_invoice_keeps_existing_and_adds_declaration(self):
        merged = merge_invoice_cancel_ignore_doctypes("Sales Invoice", ["Journal Entry"])
        self.assertEqual(merged[0], "Journal Entry")
        self.assertIn("Declaration", merged)
        self.assertIn("Transport Job", merged)

    def test_purchase_invoice_json_string_is_merged(self):
        merged = merge_invoice_cancel_ignore_doctypes("Purchase Invoice", '["Payment Entry"]')
        self.assertEqual(merged[0], "Payment Entry")
        self.assertIn("Declaration", merged)

    def test_other_doctype_is_unchanged(self):
        self.assertEqual(
            merge_invoice_cancel_ignore_doctypes("Declaration", ["Journal Entry"]),
            ["Journal Entry"],
        )

    def test_missing_list_on_invoice_is_the_job_list(self):
        merged = merge_invoice_cancel_ignore_doctypes("Sales Invoice", None)
        self.assertIn("Declaration", merged)
        self.assertNotIn("Journal Entry", merged)

    def test_desk_script_lists_the_same_jobs(self):
        script = pathlib.Path(__file__).resolve().parents[2] / "public/js/sales_invoice_job_dimension_cleanup.js"
        text = script.read_text()
        for doctype in INVOICE_CANCEL_PRESERVED_JOBS:
            self.assertIn(f'"{doctype}"', text)

    def test_extend_ignore_linked_doctypes_keeps_erpnext_entries(self):
        doc = frappe._dict(ignore_linked_doctypes=("GL Entry", "Payment Ledger Entry"))
        extend_invoice_ignore_linked_doctypes(doc)
        self.assertEqual(doc.ignore_linked_doctypes[0], "GL Entry")
        self.assertIn("Payment Ledger Entry", doc.ignore_linked_doctypes)
        self.assertIn("Declaration", doc.ignore_linked_doctypes)


class TestCancelLinkedDocsWrappers(UnitTestCase):
    def test_get_submitted_linked_docs_passes_merged_ignore_list(self):
        with patch(
            "frappe.desk.form.linked_with.get_submitted_linked_docs",
            return_value={"docs": [], "count": 0},
        ) as original:
            get_submitted_linked_docs("Sales Invoice", "ACC-SINV-1", ["Journal Entry"])

        ignore = original.call_args.args[2]
        self.assertEqual(original.call_args.args[0], "Sales Invoice")
        self.assertEqual(original.call_args.args[1], "ACC-SINV-1")
        self.assertEqual(ignore[0], "Journal Entry")
        self.assertIn("Declaration", ignore)

    def test_cancel_all_linked_docs_passes_merged_ignore_list(self):
        docs = [{"doctype": "Declaration", "name": "CD0000000006", "docstatus": 1}]
        with patch("frappe.desk.form.linked_with.cancel_all_linked_docs") as original:
            cancel_all_linked_docs(
                docs=docs,
                ignore_doctypes_on_cancel_all=["Journal Entry"],
                root_doctype="Sales Invoice",
                root_name="ACC-SINV-2026-00011",
            )

        kwargs = original.call_args.kwargs
        self.assertEqual(kwargs["docs"], docs)
        self.assertEqual(kwargs["root_doctype"], "Sales Invoice")
        self.assertEqual(kwargs["root_name"], "ACC-SINV-2026-00011")
        self.assertEqual(kwargs["ignore_doctypes_on_cancel_all"][0], "Journal Entry")
        self.assertIn("Declaration", kwargs["ignore_doctypes_on_cancel_all"])

    def test_cancel_all_for_other_root_does_not_add_jobs(self):
        with patch("frappe.desk.form.linked_with.cancel_all_linked_docs") as original:
            cancel_all_linked_docs(
                docs=[],
                ignore_doctypes_on_cancel_all=["Journal Entry"],
                root_doctype="Sales Order",
                root_name="SO-1",
            )

        self.assertEqual(
            original.call_args.kwargs["ignore_doctypes_on_cancel_all"],
            ["Journal Entry"],
        )
