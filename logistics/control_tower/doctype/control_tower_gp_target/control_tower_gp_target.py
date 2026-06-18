# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document


class ControlTowerGPTarget(Document):
	def validate(self):
		if (self.target_amount or 0) < 0:
			frappe.throw(_("Target Amount cannot be negative."))
