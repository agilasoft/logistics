# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import unittest

from logistics.cash_advance.doc_event_shadows import clear_doc_event_method_shadows


class TestDocEventMethodShadows(unittest.TestCase):
	def test_clear_doc_event_method_shadows_removes_null_lifecycle_keys(self):
		doc = type("Doc", (), {})()
		doc.__dict__["before_submit"] = None
		doc.__dict__["on_submit"] = None
		doc.__dict__["total_requested"] = 500

		clear_doc_event_method_shadows(doc)

		self.assertNotIn("before_submit", doc.__dict__)
		self.assertNotIn("on_submit", doc.__dict__)
		self.assertEqual(doc.__dict__["total_requested"], 500)
