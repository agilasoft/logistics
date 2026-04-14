# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Transport Order Charges.unit_rate to rate (align with Air Booking Charges)."""

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	dt = "Transport Order Charges"
	if not frappe.db.exists("DocType", dt):
		return
	meta = frappe.get_meta(dt, cached=False)
	if meta.get_field("unit_rate") and not meta.get_field("rate"):
		rename_field(dt, "unit_rate", "rate")
	frappe.db.commit()
