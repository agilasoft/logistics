# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

from frappe.model.document import Document
from frappe.utils import flt


class PipelineEntry(Document):
	def validate(self):
		gp = flt(self.estimated_gp)
		pct = flt(self.probability_pct)
		self.weighted_gp = gp * (pct / 100.0) if pct else 0.0
