# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Delete all Customer masters on a demo site (e.g. before a clean re-import).

Dry run first:

    bench --site atndemo.s.frappe.cloud execute logistics.utils.clear_demo_customers.clear_demo_customers --kwargs '{"dry_run": true}'

Live:

    bench --site atndemo.s.frappe.cloud execute logistics.utils.clear_demo_customers.clear_demo_customers --kwargs '{"dry_run": false, "confirm_site": "atndemo.s.frappe.cloud"}'

Or from System Console (imports are blocked; use frappe.call and enable Commit for live):

    frappe.call("logistics.utils.clear_demo_customers.clear_demo_customers", dry_run=1)
    frappe.call(
        "logistics.utils.clear_demo_customers.clear_demo_customers",
        dry_run=0,
        confirm_site=frappe.local.site,
    )
"""

from __future__ import annotations

import frappe
from frappe.model.rename_doc import get_link_fields


@frappe.whitelist()
def clear_demo_customers(dry_run=True, confirm_site=None, commit_every=50):
	"""Remove every Customer on the current site."""
	frappe.only_for("System Manager")
	site = frappe.local.site
	if not dry_run and confirm_site != site:
		frappe.throw(
			f"Pass confirm_site='{site}' to delete customers on this site. "
			"Live delete refused without an explicit matching site name."
		)

	names = frappe.get_all("Customer", pluck="name", order_by="name asc")
	print(f"Site: {site}")
	print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
	print(f"Customers to delete: {len(names)}")

	if dry_run:
		print("\nDry run only. Run again with dry_run=False to delete.")
		return {"dry_run": True, "site": site, "count": len(names)}

	frappe.set_user("Administrator")
	frappe.flags.ignore_links = True

	print("\nUnlinking Customer from other documents...")
	_unlink_customers(names)
	frappe.db.commit()

	failed = []
	print(f"\nDeleting {len(names)} Customer records...")
	for i, name in enumerate(names, 1):
		try:
			frappe.delete_doc("Customer", name, force=1, ignore_permissions=True)
		except Exception as e:
			failed.append((name, str(e)[:240]))
			print(f"  FAIL delete {name}: {e}")
		if i % commit_every == 0:
			frappe.db.commit()
			print(f"  ... {i}/{len(names)}")

	frappe.db.commit()
	frappe.clear_cache(doctype="Customer")

	remaining = frappe.db.count("Customer")
	print(f"\nDeleted attempted: {len(names)}")
	print(f"Remaining: {remaining}")
	print(f"Failed: {len(failed)}")
	for name, err in failed[:40]:
		print(f"  {name}: {err}")
	if not failed and remaining == 0:
		print("Done.")

	return {
		"dry_run": False,
		"site": site,
		"deleted": len(names) - len(failed),
		"remaining": remaining,
		"failed": failed,
	}


def _unlink_customers(names):
	if not names:
		if frappe.db.table_exists("Dynamic Link"):
			frappe.db.delete("Dynamic Link", {"link_doctype": "Customer"})
		return

	try:
		link_fields = get_link_fields("Customer")
	except Exception:
		link_fields = []

	name_set = set(names)
	chunks = [names[i : i + 500] for i in range(0, len(names), 500)]
	for lf in link_fields:
		parent = lf.parent
		field = lf.fieldname
		if not parent or not field or parent == "Customer":
			continue
		if not frappe.db.table_exists(parent):
			continue
		try:
			if int(lf.issingle or 0):
				val = frappe.db.get_single_value(parent, field)
				if val in name_set:
					frappe.db.set_single_value(parent, field, None)
				continue
			for chunk in chunks:
				frappe.db.sql(
					f"UPDATE `tab{parent}` SET `{field}` = NULL WHERE `{field}` IN %(names)s",
					{"names": chunk},
				)
		except Exception as e:
			print(f"  skip {parent}.{field}: {e}")

	if frappe.db.table_exists("Dynamic Link"):
		for chunk in chunks:
			frappe.db.sql(
				"""
				DELETE FROM `tabDynamic Link`
				WHERE link_doctype = 'Customer' AND link_name IN %(names)s
				""",
				{"names": chunk},
			)

	if frappe.db.table_exists("User Permission"):
		frappe.db.delete("User Permission", {"allow": "Customer"})
