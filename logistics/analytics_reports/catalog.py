# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Management KPI Script Report definitions per workspace module.

Each entry is ``(report_title, ref_doctype, handler_id, options_dict)``. Raw titles in
``management_definitions`` are normalized to **Proper Case** (articles ``a``, ``an``,
``the`` lowercase except when first). Titles must contain only letters, digits, spaces,
and hyphens so ``frappe.scrub(report_title)`` matches the on-disk report folder. Handlers are implemented in
``logistics.analytics_reports.management_reports`` (see ``HANDLERS``).

There are **20** reports per module. Row definitions live in
``management_definitions.RAW_REPORTS_BY_MODULE``.
"""

from __future__ import unicode_literals

import re

from logistics.analytics_reports.management_definitions import RAW_REPORTS_BY_MODULE

# Lowercase when not the first word of the title (Chicago-style articles).
_ARTICLES = frozenset({"a", "an", "the"})


def _proper_case_title(title):
	"""Title Case with ``a`` / ``an`` / ``the`` lowercase except as the first word."""
	if not title:
		return title

	def _case_segment(segment, is_first_in_title):
		if not segment:
			return segment
		suffix = ""
		s = segment
		while len(s) > 1 and s[-1] in ",.;:!?":
			suffix = s[-1] + suffix
			s = s[:-1]
		if not s:
			return segment
		s_lower = s.lower()
		if not is_first_in_title and s_lower in _ARTICLES:
			cased = s_lower
		elif s.isalpha() and s.isupper() and len(s) >= 2:
			cased = s
		else:
			cased = s[0:1].upper() + (s[1:].lower() if len(s) > 1 else "")
		return cased + suffix

	def _case_word(word, is_first_in_title):
		if "-" in word:
			parts = word.split("-")
			return "-".join(
				_case_segment(parts[j], is_first_in_title and j == 0) for j in range(len(parts))
			)
		return _case_segment(word, is_first_in_title)

	words = title.split()
	return " ".join(_case_word(w, i == 0) for i, w in enumerate(words))


def f_scrub(txt):
	"""Match ``frappe.scrub``: spaces and hyphens become underscores, lowercased."""
	t = txt if isinstance(txt, str) else str(txt)
	return t.replace(" ", "_").replace("-", "_").lower()


def _assert_scrub_safe(module_label, title):
	key = f_scrub(title)
	if not key or not re.match(r"^[a-z0-9_]+$", key):
		raise ValueError(
			"Module {0!r}: report title must scrub to a valid identifier, got {1!r} -> {2!r}".format(
				module_label, title, key
			)
		)
	return key


def _finalize(module_label, rows):
	seen = set()
	out = []
	for row in rows:
		if len(row) != 4:
			raise ValueError("Module {0!r}: expected 4-tuple rows, got {1!r}".format(module_label, row))
		title, ref, handler_id, options = row
		if not isinstance(options, dict):
			raise ValueError("Module {0!r}: options must be a dict, got {1!r}".format(module_label, type(options)))
		title = _proper_case_title(title)
		key = _assert_scrub_safe(module_label, title)
		if key in seen:
			raise ValueError("Module {0!r}: duplicate scrubbed report key {1!r}".format(module_label, key))
		seen.add(key)
		out.append((title, ref, handler_id, options))
	if len(out) != 20:
		raise ValueError("Module {0!r}: expected 20 reports, got {1}".format(module_label, len(out)))
	return out


REPORTS_BY_MODULE = {label: _finalize(label, rows) for label, rows in RAW_REPORTS_BY_MODULE.items()}


def assert_complete_catalog():
	"""Development guard: catalog rows are ``(title, ref, handler_id, options)``."""
	for label, rows in REPORTS_BY_MODULE.items():
		if len(rows) != 20:
			raise ValueError("Module {0!r}: expected 20 reports, got {1}".format(label, len(rows)))
		for row in rows:
			if len(row) != 4:
				raise ValueError("Module {0!r}: bad row {1!r}".format(label, row))
			_assert_scrub_safe(label, row[0])


assert_complete_catalog()
