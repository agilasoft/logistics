# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Seed default Get Charges from Quotation filter settings rows."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Get Charges from Quotation Settings"):
		return
	from logistics.utils.get_charges_from_quotation import seed_gcfq_filter_settings_if_empty

	seed_gcfq_filter_settings_if_empty()
