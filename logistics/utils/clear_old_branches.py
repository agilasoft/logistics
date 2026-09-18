# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Clear old Branch records so they can be deleted.

Keeps the actual Branch names you pass in. Every other Branch is unlinked
from documents (jobs, invoices, employees, settings, etc.) then deleted.

Dry run first:

    bench --site atndemo.s.frappe.cloud console

    from logistics.utils.clear_old_branches import clear_old_branches
    clear_old_branches(keep=["ATN Manila", "ATN Cebu"], dry_run=True)

Then run for real with dry_run=False.

To move documents onto an actual Branch instead of clearing the field:

    clear_old_branches(
        keep=["ATN Manila", "ATN Cebu"],
        replace={"Old Demo HQ": "ATN Manila"},
        dry_run=False,
    )
"""

from __future__ import annotations

import frappe
from frappe.model.rename_doc import get_link_fields


def clear_old_branches(keep=None, replace=None, dry_run=True):
	keep = [name for name in (keep or []) if name]
	replace = replace or {}

	if not keep:
		frappe.throw("Pass keep=['Actual Branch Name', ...] so those Branches are not deleted.")

	missing = [name for name in keep if not frappe.db.exists("Branch", name)]
	if missing:
		frappe.throw(f"These keep Branches do not exist: {', '.join(missing)}")

	for old, new in replace.items():
		if new not in keep and not frappe.db.exists("Branch", new):
			frappe.throw(f"replace target '{new}' is not an existing Branch.")

	to_delete = [
		name for name in frappe.get_all("Branch", pluck="name") if name not in keep
	]
	link_fields = get_link_fields("Branch")

	print(f"Keep: {keep}")
	print(f"Delete: {to_delete or '(none)'}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")

	for old in to_delete:
		new_value = replace.get(old) or ""
		action = f"reassign -> {new_value}" if new_value else "clear"
		print(f"\n{old}: {action}")
		_unlink_branch(old, new_value, link_fields, dry_run=dry_run)
		if dry_run:
			print(f"  would delete Branch {old}")
			continue
		frappe.delete_doc("Branch", old, ignore_permissions=True, force=1)
		print(f"  deleted Branch {old}")

	if not dry_run:
		frappe.db.commit()
		print("\nDone.")
	else:
		print("\nDry run only. Run again with dry_run=False to apply.")

	return {"keep": keep, "deleted": to_delete, "dry_run": dry_run}


def _unlink_branch(old, new_value, link_fields, dry_run=True):
	for lf in link_fields:
		dt = lf.parent
		fn = lf.fieldname
		if not dt or not fn or not frappe.db.table_exists(dt):
			continue

		count = _count_links(dt, fn, old, issingle=int(lf.issingle or 0))
		if not count:
			continue

		print(f"  {dt}.{fn}: {count}")
		if dry_run:
			continue

		if int(lf.issingle or 0):
			if frappe.db.get_single_value(dt, fn) == old:
				frappe.db.set_single_value(dt, fn, new_value or None)
			continue

		frappe.db.sql(
			f"UPDATE `tab{dt}` SET `{fn}` = %s WHERE `{fn}` = %s",
			(new_value, old),
		)

	if frappe.db.table_exists("Dynamic Link"):
		count = frappe.db.count(
			"Dynamic Link", {"link_doctype": "Branch", "link_name": old}
		)
		if count:
			print(f"  Dynamic Link: {count}")
			if not dry_run:
				frappe.db.sql(
					"""
					UPDATE `tabDynamic Link`
					SET link_name = %s
					WHERE link_doctype = 'Branch' AND link_name = %s
					""",
					(new_value, old),
				)

	if frappe.db.table_exists("User Permission"):
		count = frappe.db.count(
			"User Permission", {"allow": "Branch", "for_value": old}
		)
		if count:
			print(f"  User Permission: {count}")
			if not dry_run:
				frappe.db.delete(
					"User Permission", {"allow": "Branch", "for_value": old}
				)


def _count_links(dt, fn, old, issingle=0):
	if issingle:
		return 1 if frappe.db.get_single_value(dt, fn) == old else 0
	try:
		return frappe.db.count(dt, {fn: old})
	except Exception:
		return 0
