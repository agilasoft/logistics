# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Customs desktop tile route.

Frappe's desktop grid builds the href in ``get_route()``:

* ``link_type == "External"`` uses ``link`` as the path, so ``/app/customs``
  opens the old ``/app`` prefix.
* ``link_type == "Workspace Sidebar"`` asks the module sidebar for its home.
  Customs' first item is the Customs workspace, which the desk spells
  ``/desk/customs``.
* A set ``sidebar`` skips ``get_route()`` entirely, and the tile then reports
  that it is not configured.

``/app`` is the desk's previous prefix. The other logistics tiles never
hard-code it.
"""

from __future__ import annotations

CUSTOMS_LABEL = "Customs"

# Keys the grid reads. ``link`` and ``sidebar`` stay empty so the External
# branch and the "sidebar is set" skip cannot win.
DESK_ROUTE = {
	"link_type": "Workspace Sidebar",
	"link_to": CUSTOMS_LABEL,
	"link": None,
	"sidebar": None,
}


def is_customs_tile(icon: dict) -> bool:
	"""The standard Customs tile, including a copy nested in a desktop folder."""
	if not isinstance(icon, dict):
		return False
	if icon.get("label") != CUSTOMS_LABEL:
		return False
	return icon.get("name") in (None, CUSTOMS_LABEL)


def apply_desk_route(icon: dict) -> bool:
	"""Point one layout icon at the Customs desk. Return whether it changed."""
	if not is_customs_tile(icon):
		return False
	changed = False
	for key, value in DESK_ROUTE.items():
		if icon.get(key) != value:
			icon[key] = value
			changed = True
	return changed


def apply_desk_route_to_doc(doc) -> bool:
	"""Point the Customs Desktop Icon document at the desk. Return whether it changed."""
	changed = False
	for key, value in DESK_ROUTE.items():
		if getattr(doc, key, None) != value:
			setattr(doc, key, value)
			changed = True
	return changed


def walk_icons(layout) -> bool:
	"""Rewrite Customs inside a Desktop Layout list, including folder children."""
	if not isinstance(layout, list):
		return False
	changed = False
	for icon in layout:
		if not isinstance(icon, dict):
			continue
		if apply_desk_route(icon):
			changed = True
		children = icon.get("child_icons") or []
		if isinstance(children, list) and walk_icons(children):
			changed = True
	return changed
