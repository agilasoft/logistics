# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe

DEFAULT_SEA_CUT_OFFS = (
	"Cargo Cut-offs",
	"Documents Cut-offs",
	"VGM Cut-offs",
	"Other Cut-offs",
)


def after_migrate():
	if frappe.flags.in_install:
		return
	ensure_default_sea_cut_offs()


def ensure_default_sea_cut_offs():
	if not frappe.db.exists("DocType", "Sea Cut Off"):
		return

	for cut_off_name in DEFAULT_SEA_CUT_OFFS:
		if frappe.db.exists("Sea Cut Off", cut_off_name):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Sea Cut Off",
				"cut_off_name": cut_off_name,
			}
		)
		doc.insert(ignore_permissions=True)
