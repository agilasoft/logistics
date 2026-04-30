# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.utils.container_validation import (
	get_strict_validation_setting,
	normalize_container_number,
	validate_container_number,
)


class SeaConsolidationContainers(Document):
	def validate(self):
		"""ISO 6346 container number (same rules as Container / Sea Booking)."""
		if not getattr(self, "container_number", None):
			return
		self.container_number = normalize_container_number(self.container_number)
		if not self.container_number:
			return
		try:
			bypass = frappe.get_request_header("X-Container-Validation-Bypass") == "1"
		except RuntimeError:
			bypass = False
		strict = get_strict_validation_setting()
		valid, err = validate_container_number(
			self.container_number,
			strict=strict,
			allow_bypass=bypass,
		)
		if not valid:
			frappe.throw(err, title=_("Invalid Container Number"))

