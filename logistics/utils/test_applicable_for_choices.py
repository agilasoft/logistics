# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import unittest
from pathlib import Path

from logistics.utils.applicable_for_choices import applicable_for_names, applicable_for_page


class TestApplicableForChoices(unittest.TestCase):
	def test_typed_company_stays_on_the_first_page(self):
		linked = [f"Doc {index:02d}" for index in range(40)]
		page = applicable_for_page("Company", linked, "Company", start=0, page_len=10)
		self.assertEqual(page[0], "Company")

	def test_empty_search_includes_the_permission_doctype_and_linked_documents(self):
		names = applicable_for_names(
			"Company",
			{
				"Sales Invoice": {
					"child_doctype": "Sales Invoice Item",
					"child_links": [{"child_doctype": "Sales Invoice Payment"}],
				}
			},
			"",
		)
		self.assertEqual(
			names,
			["Company", "Sales Invoice", "Sales Invoice Item", "Sales Invoice Payment"],
		)

	def test_desk_script_repairs_the_company_search(self):
		source = (Path(__file__).resolve().parents[1] / "public" / "js" / "applicable_for_link.js").read_text()
		self.assertIn("logistics.utils.applicable_for_query.applicable_for_query", source)
		self.assertIn("args.doctype = link_doctype", source)
		self.assertIn("doctype: reference", source)
