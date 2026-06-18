"""
Ensure the ``Driver`` role can pair a phone to a Transport Vehicle by writing
the ``gotransport_device`` field via ``frappe.client.set_value``.

Background
----------
``frappe.client.set_value`` ultimately calls ``doc.save()`` which checks
``write`` permission at **permlevel 0** — independent of the field's own
permlevel. A previous attempt isolated ``gotransport_device`` on permlevel 1
and only granted Driver write on permlevel 1, which still produced a 403 on
save.

This patch normalises the permission model:

* Drops the Property Setter that pushed ``gotransport_device`` to permlevel 1.
* Drops any Custom DocPerm for ``Driver`` at permlevel > 0 on Transport Vehicle
  (no longer needed).
* Ensures a single Custom DocPerm for ``Driver`` at permlevel 0 on
  Transport Vehicle with ``read=1, write=1`` (and ``create=0, delete=0``).

The DocType meta cache is cleared at the end so the change is visible to
running web/worker processes without a manual restart.
"""

import frappe


DOCTYPE = "Transport Vehicle"
ROLE = "Driver"
FIELD = "gotransport_device"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	if not frappe.db.exists("Role", ROLE):
		return

	_drop_permlevel_property_setter()
	_drop_high_permlevel_driver_perms()
	_ensure_driver_baseline_perm()

	frappe.clear_cache(doctype=DOCTYPE)


def _drop_permlevel_property_setter():
	ps_name = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": DOCTYPE,
			"field_name": FIELD,
			"property": "permlevel",
		},
		"name",
	)
	if ps_name:
		frappe.delete_doc("Property Setter", ps_name, ignore_permissions=True, force=True)


def _drop_high_permlevel_driver_perms():
	rows = frappe.db.get_all(
		"Custom DocPerm",
		filters={"parent": DOCTYPE, "role": ROLE, "permlevel": (">", 0)},
		pluck="name",
	)
	for name in rows:
		frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True, force=True)


def _ensure_driver_baseline_perm():
	existing = frappe.db.get_value(
		"Custom DocPerm",
		{"parent": DOCTYPE, "role": ROLE, "permlevel": 0},
		"name",
	)
	if existing:
		doc = frappe.get_doc("Custom DocPerm", existing)
		doc.read = 1
		doc.write = 1
		if doc.create is None:
			doc.create = 0
		if doc.delete is None:
			doc.delete = 0
		doc.save(ignore_permissions=True)
		return

	doc = frappe.new_doc("Custom DocPerm")
	doc.update(
		{
			"parent": DOCTYPE,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": ROLE,
			"permlevel": 0,
			"read": 1,
			"write": 1,
			"create": 0,
			"delete": 0,
			"submit": 0,
			"cancel": 0,
			"amend": 0,
		}
	)
	doc.insert(ignore_permissions=True)
