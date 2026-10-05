# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""The programme desk tile is MICE. Exhibits is not a second dock label."""

from __future__ import annotations

EXHIBITS_LABEL = "Exhibits"
MICE_LABEL = "MICE"


def relabel_desk_layout(layout):
	"""Return a desktop layout that shows MICE instead of Exhibits.

	A layout that already has MICE drops the Exhibits tile. A layout that only
	has Exhibits keeps that tile and names it MICE.
	"""
	if not isinstance(layout, list):
		return layout
	mice_present = any(isinstance(icon, dict) and _is_mice(icon) for icon in layout)
	result = []
	for icon in layout:
		if not isinstance(icon, dict) or not _is_exhibits(icon):
			result.append(icon)
			continue
		if mice_present:
			continue
		result.append(_as_mice(icon))
		mice_present = True
	return result


def _is_mice(icon):
	return icon.get("label") == MICE_LABEL or icon.get("link_to") == MICE_LABEL


def _is_exhibits(icon):
	return icon.get("label") == EXHIBITS_LABEL or icon.get("link_to") == EXHIBITS_LABEL


def _as_mice(icon):
	updated = dict(icon)
	if updated.get("label") == EXHIBITS_LABEL:
		updated["label"] = MICE_LABEL
	if updated.get("link_to") == EXHIBITS_LABEL:
		updated["link_to"] = MICE_LABEL
	if updated.get("name") == EXHIBITS_LABEL:
		updated["name"] = MICE_LABEL
	return updated
