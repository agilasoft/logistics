# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Place Workflow Center on each logistics module workspace and sidebar.

Control Tower is the pattern: a top-level sidebar link under Home, and a
Quick Access shortcut on the module workspace. Workflow Center is one page,
so every module opens the same route.
"""

from __future__ import annotations

import html
import json
import re

LABEL = "Workflow Center"
PAGE = "workflow-center"
ICON = "workflow"
ACCESS_HEADERS = {"Quick Access", "Shortcuts"}


def apply_workspace(workspace: dict) -> bool:
	"""Insert the Workflow Center shortcut. Returns True when the document changed."""
	shortcuts = workspace.setdefault("shortcuts", [])
	raw_content = workspace.get("content") or "[]"
	as_text = isinstance(raw_content, str)
	blocks = json.loads(raw_content) if as_text else list(raw_content)

	changed = False
	if not _content_has_link(blocks):
		blocks.insert(_content_insert_index(blocks), _content_block())
		changed = True
	if not any(row.get("label") == LABEL for row in shortcuts):
		shortcuts.insert(_shortcut_insert_index(shortcuts), _shortcut_row())
		changed = True
	if changed and as_text:
		workspace["content"] = _dump_content(blocks, raw_content)
	elif changed:
		workspace["content"] = blocks
	return changed


def apply_sidebar(sidebar: dict) -> bool:
	"""Insert the Workflow Center link under Home (or under Control Tower)."""
	items = sidebar.setdefault("items", [])
	if any(item.get("label") == LABEL and item.get("type") != "Section Break" for item in items):
		return False
	template = next((item for item in items if item.get("label") == "Home"), {})
	items.insert(_sidebar_insert_index(items), _sidebar_item(template))
	for index, item in enumerate(items, start=1):
		item["idx"] = index
	return True


def _content_has_link(blocks: list) -> bool:
	return any(
		block.get("type") == "shortcut" and (block.get("data") or {}).get("shortcut_name") == LABEL
		for block in blocks
	)


def _content_insert_index(blocks: list) -> int:
	for index, block in enumerate(blocks):
		data = block.get("data") or {}
		if block.get("type") == "shortcut" and data.get("shortcut_name") == "Control Tower":
			return index + 1
	for index, block in enumerate(blocks):
		if block.get("type") == "header" and _header_text(block) in ACCESS_HEADERS:
			for cursor in range(index + 1, len(blocks)):
				kind = blocks[cursor].get("type")
				if kind in ("shortcut", "header"):
					return cursor
			return len(blocks)
	for index, block in enumerate(blocks):
		if block.get("type") == "header":
			return index + 1
	return 0


def _shortcut_insert_index(shortcuts: list) -> int:
	for index, row in enumerate(shortcuts):
		if row.get("label") == "Control Tower":
			return index + 1
	return 0


def _sidebar_insert_index(items: list) -> int:
	for index, item in enumerate(items):
		if item.get("label") == "Control Tower" and item.get("type") != "Section Break":
			return index + 1
	for index, item in enumerate(items):
		if item.get("label") == "Home":
			return index + 1
	return 0


def _header_text(block: dict) -> str:
	text = (block.get("data") or {}).get("text") or ""
	return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _content_block() -> dict:
	return {"id": "wfcQuick01", "type": "shortcut", "data": {"shortcut_name": LABEL, "col": 3}}


def _shortcut_row() -> dict:
	return {
		"color": "Blue",
		"doc_view": "",
		"label": LABEL,
		"link_to": PAGE,
		"type": "Page",
	}


def _sidebar_item(template: dict) -> dict:
	values = {
		"child": 0,
		"collapsible": template.get("collapsible", 1),
		"doctype": "Sidebar Item",
		"icon": ICON,
		"idx": 0,
		"indent": 0,
		"keep_closed": 0,
		"label": LABEL,
		"link_to": PAGE,
		"link_type": "Page",
		"parentfield": template.get("parentfield", "items"),
		"parenttype": template.get("parenttype", "Sidebar"),
		"show_arrow": 0,
		"type": "Link",
	}
	if template:
		item = {key: values[key] for key in template if key in values}
		for key, value in values.items():
			item.setdefault(key, value)
		return item
	return values


def _dump_content(blocks: list, original: str) -> str:
	if '": "' in original:
		return json.dumps(blocks)
	return json.dumps(blocks, separators=(",", ":"))
