# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Choices for the Applicable For link on a user permission.

The permission's own document type is always included. A Company permission can
therefore apply to Company itself, which keeps that company on the company list
without opening every document that belongs to it.
"""

from __future__ import annotations


def clean_text(value) -> str:
	return " ".join(str(value or "").split())


def applicable_for_names(reference_doctype: str, linked=None, txt: str = "") -> list[str]:
	"""Document types that match the typed text.

	An exact match is placed first. Link validation only reads the first page of
	results, so the typed name has to be on that page or the field clears it.
	"""
	names = []
	reference = clean_text(reference_doctype)
	if reference:
		names.append(reference)
	names.extend(_linked_doctype_names(linked))
	query = clean_text(txt).casefold()
	unique = sorted(set(names), key=str.casefold)
	if query:
		unique = [name for name in unique if query in name.casefold()]
	exact = [name for name in unique if name.casefold() == query]
	rest = [name for name in unique if name.casefold() != query]
	return exact + rest


def applicable_for_page(reference_doctype: str, linked, txt: str, start=0, page_len=20) -> list[str]:
	names = applicable_for_names(reference_doctype, linked, txt)
	start_index = _page_start(start)
	return names[start_index : start_index + _page_size(page_len)]


def _linked_doctype_names(linked) -> list[str]:
	if not linked:
		return []
	if isinstance(linked, (list, tuple, set)):
		return [name for name in (clean_text(item) for item in linked) if name]
	if not isinstance(linked, dict):
		return []
	names = []
	for key, value in linked.items():
		cleaned = clean_text(key)
		if cleaned:
			names.append(cleaned)
		if not isinstance(value, dict):
			continue
		child = clean_text(value.get("child_doctype"))
		if child:
			names.append(child)
		for child_link in value.get("child_links") or []:
			if isinstance(child_link, dict):
				nested = clean_text(child_link.get("child_doctype"))
				if nested:
					names.append(nested)
	return names


def _page_start(start) -> int:
	try:
		return max(int(start or 0), 0)
	except (TypeError, ValueError):
		return 0


def _page_size(page_len) -> int:
	try:
		size = int(page_len or 20)
	except (TypeError, ValueError):
		return 20
	return size if size > 0 else 20
