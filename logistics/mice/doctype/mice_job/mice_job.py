# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document



class MICEJob(Document):
	def validate(self):
		from logistics.utils.document_date_validation import validate_planned_date_range

		validate_planned_date_range(self)
		self._sync_from_exhibit()

	def _sync_from_exhibit(self):
		"""Sync defaults from the linked MICE Project.

		- ``project`` always tracks the Project on the parent MICE Project (it's
		  the ERPNext Project used as Accounting Dimension on every posting).
		- ``customer`` defaults from the parent's Organizer (``MICE Organizer.customer``)
		  when blank. ``MICE Project`` no longer carries a direct Customer link.
		- ``ep_customer`` is a read-only mirror of the Organizer's billing
		  Customer used in the From-MICE-Project header. Populated here because
		  the old ``fetch_from`` chain (exhibit.customer) was removed.
		"""
		if not self.exhibit:
			return
		row = frappe.db.get_value(
			"MICE Project",
			self.exhibit,
			["organizer", "project"],
			as_dict=True,
		)
		if not row:
			return

		organizer_customer = None
		if row.get("organizer"):
			organizer_customer = (
				frappe.db.get_value("MICE Organizer", row.get("organizer"), "customer")
				or None
			)

		if organizer_customer and not self.customer:
			self.customer = organizer_customer

		if hasattr(self, "ep_customer"):
			self.ep_customer = organizer_customer

		if row.get("project") and not self.get("project"):
			self.project = row.project
