# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Seed the Permit Type used by Declaration Type Application."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Permit Type"):
		return
	from logistics.customs.permit_application_only import ensure_permit_application_only_type

	ensure_permit_application_only_type()
