# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""MICE Organizer master.

Represents the programme-level organizer of a MICE Project (show organizer,
association, government body, individual, etc.). Optionally linked to an
ERPNext Customer so downstream Dockets / MICE Jobs / MICE Orders can resolve
their billing Customer from ``MICE Project -> MICE Organizer.customer``.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document


class MICEOrganizer(Document):
	def onload(self):
		"""Render Address / Contact dynamic-link panels."""
		load_address_and_contact(self)

	def validate(self):
		self._normalize_website()

	def _normalize_website(self):
		"""Strip whitespace on the website field so duplicate detection works."""
		if self.website:
			self.website = self.website.strip()

	def on_trash(self):
		delete_contact_and_address(self.doctype, self.name)
