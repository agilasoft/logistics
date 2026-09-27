# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Based on Specified Charge Group to calculation method fields on charge and rate doctypes."""

import frappe

from logistics.patches.v3_0_add_specified_charges_option import CHARGE_DOCTYPES, METHOD_FIELDS


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		updated = False
		for fieldname in METHOD_FIELDS:
			field = meta.get_field(fieldname)
			if not field or not field.options:
				continue
			opts = field.options or ""
			if "Based on Specified Charge Group" in opts:
				continue
			new_opts = opts.rstrip() + "\nBased on Specified Charge Group"
			frappe.db.set_value(
				"DocField",
				{"parent": dt, "fieldname": fieldname},
				"options",
				new_opts,
			)
			updated = True
		if updated:
			frappe.clear_cache(doctype=dt)
	frappe.db.commit()
