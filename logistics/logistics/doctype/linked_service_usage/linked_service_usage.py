# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from frappe.model.document import Document


class LinkedServiceUsage(Document):
	"""Child row: one consumer (booking / order / job) of a Linked Service ID."""

	pass
