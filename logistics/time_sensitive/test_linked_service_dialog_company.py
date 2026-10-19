# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Company choices in the services dialog follow the Linked Service form."""

import unittest
from pathlib import Path


DIALOG_JS = (
	Path(__file__).resolve().parents[1] / "public" / "js" / "linked_services_dialog.js"
)


def visible_companies(permissions, reference_doctype):
	"""Companies a link search keeps, matching Frappe user permissions.

	A permission with Applicable For is included only when the link's
	reference doctype is that document. Permissions with no Applicable For
	always remain.
	"""
	names = []
	for permission in permissions:
		applicable_for = permission.get("applicable_for")
		if not applicable_for:
			names.append(permission["doc"])
		elif reference_doctype and applicable_for == reference_doctype:
			names.append(permission["doc"])
	return names


class TestLinkedServiceDialogCompany(unittest.TestCase):
	def test_dialog_link_search_uses_linked_service_context(self):
		source = DIALOG_JS.read_text()
		mount = source.split("function _lsd1_mount_edit_field", 1)[1].split(
			"function _lsd1_collect_control_values", 1
		)[0]
		self.assertIn('parent: "Linked Service"', mount)
		self.assertIn('doctype: "Linked Service"', mount)

	def test_linked_service_context_includes_tagged_companies(self):
		permissions = [
			{"doc": "ALL SYSTEMS LOGISTICS INC.", "applicable_for": ""},
			{"doc": "ALL TRANSPORT NETWORK, INC.", "applicable_for": "Linked Service"},
			{"doc": "FAST PRIME TRANSPORT CORP.", "applicable_for": "Linked Service"},
			{"doc": "PRIME WAREHOUSE DYNAMICS CORP.", "applicable_for": "Linked Service"},
		]
		self.assertEqual(
			visible_companies(permissions, ""),
			["ALL SYSTEMS LOGISTICS INC."],
		)
		self.assertEqual(
			visible_companies(permissions, "Linked Service"),
			[
				"ALL SYSTEMS LOGISTICS INC.",
				"ALL TRANSPORT NETWORK, INC.",
				"FAST PRIME TRANSPORT CORP.",
				"PRIME WAREHOUSE DYNAMICS CORP.",
			],
		)
