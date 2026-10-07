# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""The programme desk tile is MICE. Exhibits is not a second dock label."""

from __future__ import annotations

EXHIBITS_LABEL = "Exhibits"
MICE_LABEL = "MICE"
MICE_APP = "logistics"

# Saved layouts nest folder contents here. The grid also stores a flat list.
_CHILD_KEYS = ("child_icons",)


def relabel_desk_layout(layout, mice_present=None):
	"""Return a desktop layout that shows MICE instead of Exhibits.

	A layout that already has MICE drops the Exhibits tile. A layout that only
	has Exhibits keeps that tile and names it MICE. Folder contents are walked
	the same way, so a tile filed inside a folder is not left behind.
	"""
	if not isinstance(layout, list):
		return layout
	if mice_present is None:
		mice_present = _tree_has_mice(layout)
	result = []
	for icon in layout:
		if not isinstance(icon, dict):
			result.append(icon)
			continue
		if mice_present and _is_exhibits(icon):
			continue
		updated = dict(icon)
		for key in _CHILD_KEYS:
			children = updated.get(key)
			if isinstance(children, list):
				updated[key] = relabel_desk_layout(children, mice_present)
		if _is_exhibits(updated):
			updated = _as_mice(updated)
		elif _is_mice(updated):
			updated = _stamp_mice(updated)
		result.append(updated)
	return result


def extend_bootinfo(bootinfo) -> None:
	"""Drop a stale Exhibits tile from the desk payload for this request.

	``get_desktop_icons`` reads ``tabDesktop Icon``. A row left over from the
	Exhibits name, or a saved layout that still says Exhibits, is what the
	grid draws. Renaming it here covers a request that arrives before migrate
	has rewritten those rows.

	The route still follows the Exhibits shell when that is the only sidebar
	the desk has built. The label is MICE either way.
	"""
	if bootinfo is None:
		return
	icons = bootinfo.get("desktop_icons") if hasattr(bootinfo, "get") else None
	if not icons:
		return
	relabeled = relabel_desk_layout(list(icons))
	sidebars = bootinfo.get("module_sidebars") or {}
	if _shell_exists(sidebars, EXHIBITS_LABEL) and not _shell_exists(sidebars, MICE_LABEL):
		for icon in relabeled:
			if isinstance(icon, dict) and icon.get("label") == MICE_LABEL:
				icon["module"] = EXHIBITS_LABEL
	bootinfo.desktop_icons = relabeled


def _shell_exists(sidebars, name: str) -> bool:
	if not isinstance(sidebars, dict):
		return False
	if name in sidebars:
		return True
	for entry in sidebars.values():
		if isinstance(entry, dict) and name in (entry.get("module"), entry.get("title"), entry.get("name")):
			return True
	return False


def after_migrate() -> None:
	"""Keep the desk tile named MICE after every migrate."""
	sync_desk()


def sync_desk() -> None:
	"""Import the MICE tile and remove every Exhibits desk row."""
	import frappe

	_import_mice_icon()
	_normalize_mice_icon()
	for doctype in ("Desktop Icon", "Workspace Sidebar", "Workspace", "Sidebar"):
		_remove_exhibits_rows(doctype)
	_relabel_saved_layouts()
	frappe.clear_cache()
	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")


def _tree_has_mice(layout) -> bool:
	for icon in layout:
		if not isinstance(icon, dict):
			continue
		if _is_mice(icon):
			return True
		for key in _CHILD_KEYS:
			children = icon.get(key)
			if isinstance(children, list) and _tree_has_mice(children):
				return True
	return False


def _is_mice(icon) -> bool:
	return icon.get("label") == MICE_LABEL or icon.get("link_to") == MICE_LABEL or icon.get("name") == MICE_LABEL


def _is_exhibits(icon) -> bool:
	return (
		icon.get("label") == EXHIBITS_LABEL
		or icon.get("link_to") == EXHIBITS_LABEL
		or icon.get("name") == EXHIBITS_LABEL
	)


def _as_mice(icon) -> dict:
	updated = dict(icon)
	if updated.get("label") == EXHIBITS_LABEL:
		updated["label"] = MICE_LABEL
	if updated.get("link_to") == EXHIBITS_LABEL:
		updated["link_to"] = MICE_LABEL
	if updated.get("name") == EXHIBITS_LABEL:
		updated["name"] = MICE_LABEL
	if updated.get("module") == EXHIBITS_LABEL:
		updated["module"] = MICE_LABEL
	return _stamp_mice(updated)


def _stamp_mice(icon) -> dict:
	updated = dict(icon)
	if not updated.get("app"):
		updated["app"] = MICE_APP
	return updated


def _import_mice_icon() -> None:
	import os

	import frappe
	from frappe.modules.import_file import import_file_by_path
	from frappe.modules.utils import get_app_level_directory_path

	if frappe.db.table_exists("tabDesktop Icon") and frappe.db.exists("Desktop Icon", MICE_LABEL):
		return
	path = os.path.join(get_app_level_directory_path("desktop_icon", MICE_APP), "mice.json")
	if not os.path.isfile(path):
		return
	try:
		import_file_by_path(path, force=True)
	except Exception:
		frappe.log_error(title="MICE desk icon import", message=frappe.get_traceback())


def _normalize_mice_icon() -> None:
	import frappe

	if not frappe.db.table_exists("tabDesktop Icon"):
		return
	if not frappe.db.exists("Desktop Icon", MICE_LABEL):
		return
	values = {
		"app": MICE_APP,
		"bg_color": "blue",
		"label": MICE_LABEL,
		"link_to": MICE_LABEL,
		"link_type": "Workspace Sidebar",
		"hidden": 0,
		"standard": 1,
	}
	meta = frappe.get_meta("Desktop Icon")
	values = {field: value for field, value in values.items() if meta.has_field(field)}
	if values:
		frappe.db.set_value("Desktop Icon", MICE_LABEL, values, update_modified=False)


def _remove_exhibits_rows(doctype: str) -> None:
	import frappe

	if not frappe.db.table_exists(f"tab{doctype}"):
		return
	mice_exists = frappe.db.exists(doctype, MICE_LABEL)
	for name in _exhibits_row_names(doctype):
		if name == MICE_LABEL:
			_repoint_exhibits_fields(doctype, name)
			continue
		if not mice_exists and name == EXHIBITS_LABEL:
			frappe.rename_doc(doctype, EXHIBITS_LABEL, MICE_LABEL, force=True, merge=False)
			_repoint_exhibits_fields(doctype, MICE_LABEL)
			mice_exists = True
			continue
		if not mice_exists:
			_repoint_exhibits_fields(doctype, name)
			mice_exists = True
			continue
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True, ignore_missing=True)


def _exhibits_row_names(doctype: str) -> list[str]:
	import frappe

	clauses = ["`name` = %s"]
	params: list[str] = [EXHIBITS_LABEL]
	for column in ("label", "title", "link_to"):
		if frappe.db.has_column(doctype, column):
			clauses.append(f"`{column}` = %s")
			params.append(EXHIBITS_LABEL)
	rows = frappe.db.sql(
		f"SELECT `name` FROM `tab{doctype}` WHERE {' OR '.join(clauses)}",
		tuple(params),
	)
	seen = []
	for row in rows:
		name = row[0]
		if name and name not in seen:
			seen.append(name)
	return seen


def _repoint_exhibits_fields(doctype: str, name: str) -> None:
	import frappe

	values = {}
	meta = frappe.get_meta(doctype)
	for field in ("label", "title", "link_to", "module"):
		if not meta.has_field(field):
			continue
		if frappe.db.get_value(doctype, name, field) == EXHIBITS_LABEL:
			values[field] = MICE_LABEL
	if values:
		frappe.db.set_value(doctype, name, values, update_modified=False)


def _relabel_saved_layouts() -> None:
	import json

	import frappe

	if not frappe.db.table_exists("tabDesktop Layout"):
		return
	for row in frappe.get_all("Desktop Layout", fields=["name", "layout"]):
		if not row.layout:
			continue
		try:
			layout = json.loads(row.layout)
		except Exception:
			continue
		updated = relabel_desk_layout(layout)
		if updated == layout:
			continue
		frappe.db.set_value(
			"Desktop Layout",
			row.name,
			"layout",
			json.dumps(updated),
			update_modified=False,
		)
