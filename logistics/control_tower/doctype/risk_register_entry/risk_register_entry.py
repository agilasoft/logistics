# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class RiskRegisterEntry(Document):
	def validate(self):
		likelihood = cint(self.likelihood)
		impact = cint(self.impact)
		if not 1 <= likelihood <= 5:
			frappe.throw(_("Likelihood must be between 1 and 5."))
		if not 1 <= impact <= 5:
			frappe.throw(_("Impact must be between 1 and 5."))
		self.score = likelihood * impact
