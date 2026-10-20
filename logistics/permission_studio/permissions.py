# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe


def lock_hero_fields(doc, method=None):
	"""Keep ownership fields under Permission Studio's control.

	A desk user can still delete a managed User Permission. The next time its
	group is saved, Permission Studio creates it again.
	"""
	if not doc.meta.has_field("hero_managed"):
		return
	if doc.flags.get("hero_sync"):
		return
	if doc.is_new():
		doc.hero_managed = 0
		doc.hero_permission_group = None
		doc.hero_source_groups = None
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	for fieldname in ("hero_managed", "hero_permission_group", "hero_source_groups"):
		doc.set(fieldname, before.get(fieldname))
