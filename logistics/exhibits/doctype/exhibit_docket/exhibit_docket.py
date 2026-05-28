# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Virtual child table that shows every Docket linked to an Exhibit.

Rows are not persisted: the parent Exhibit populates this table in its
``onload`` from the live ``Docket`` records that reference it. The doctype is
flagged ``is_virtual: 1`` so Frappe skips all database reads/writes against
``tabExhibit Docket`` (see ``Document.load_children_from_db`` and
``Document.update_children`` in frappe).
"""

from frappe.model.document import Document


class ExhibitDocket(Document):
	def db_insert(self, *args, **kwargs):
		pass

	def db_update(self, *args, **kwargs):
		pass

	def delete(self):
		pass

	def load_from_db(self):
		pass

	@staticmethod
	def get_list(args):
		return []

	@staticmethod
	def get_count(args):
		return 0

	@staticmethod
	def get_stats(args):
		return {}
