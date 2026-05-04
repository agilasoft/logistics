# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename legacy Special Project Order / Job doctypes (and old Site Operations DB names) to Project Task *.

Runs in pre_model_sync so database DocType names match shipped JSON before migrate sync.
"""

import frappe

# Child tables first, then job, then order — for each legacy name family.
_RENAMES = (
	("Special Project Task Type", "Project Task Type"),
	("Special Project Job Resource", "Project Task Job Resource"),
	("Special Project Order Job", "Project Task Order Job"),
	("Special Project Job", "Project Task Job"),
	("Special Project Order", "Project Task Order"),
	("Site Operations Task Type", "Project Task Type"),
	("Site Operations Job Resource", "Project Task Job Resource"),
	("Site Operations Order Job", "Project Task Order Job"),
	("Site Operations Job", "Project Task Job"),
	("Site Operations Order", "Project Task Order"),
)


def execute():
	frappe.flags.in_patch = True
	try:
		for old_name, new_name in _RENAMES:
			if not frappe.db.exists("DocType", old_name):
				continue
			if frappe.db.exists("DocType", new_name):
				continue
			frappe.rename_doc(
				"DocType",
				old_name,
				new_name,
				force=True,
				merge=False,
			)
	finally:
		frappe.flags.in_patch = False
