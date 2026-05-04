# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.model.document import Document


def _digits_only(value):
	if value is None:
		return ""
	return re.sub(r"\D", "", str(value).strip())


class Vessel(Document):
	def validate(self):
		mmsi = _digits_only(self.mmsi)
		imo = _digits_only(self.imo)
		if self.mmsi and mmsi != self.mmsi:
			self.mmsi = mmsi
		if self.imo and imo != self.imo:
			self.imo = imo
		if self.mmsi and len(self.mmsi) != 9:
			frappe.throw(_("MMSI must be exactly 9 digits when set."))
		if self.imo and len(self.imo) != 7:
			frappe.throw(_("IMO must be exactly 7 digits when set."))
