# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Purchase Invoice header address from Branch Registration Details."""

from __future__ import annotations

import re

_BR_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_VAT_LINE = re.compile(r"^\s*vat\b", re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^a-z0-9]")


def header_address_from_registration(registration, company_name=None):
	"""Return the branch address printed under the company name.

	Registration Details often starts with the company name glued to the
	street (``All Transport Network, Inc.Unit 1-3A...``). That prefix is
	removed so the name is not repeated. Lines that are only a VAT TIN are
	dropped because the header already prints the branch tax id.
	"""
	text = _normalize(registration)
	if not text:
		return ""
	text = _strip_company_prefix(text, company_name)
	lines = [line.strip() for line in text.split("\n") if line.strip() and not _VAT_LINE.match(line)]
	return " ".join(lines).strip()


def _normalize(registration):
	text = registration or ""
	if not isinstance(text, str):
		text = str(text)
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	text = _BR_TAG.sub("\n", text)
	return text.strip()


def _strip_company_prefix(text, company_name):
	target = _NON_ALNUM.sub("", (company_name or "").lower())
	if not target:
		return text

	collected = []
	for index, char in enumerate(text):
		if not char.isalnum():
			continue
		collected.append(char.lower())
		so_far = "".join(collected)
		if so_far == target:
			return text[index + 1 :].lstrip(" \t.,;:")
		if not target.startswith(so_far):
			return text
	return text
