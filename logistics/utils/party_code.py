# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
"""Nine-character party codes: first 3 letters from word 1 + first 3 from word 2 + last 3 of UN/LOCODE."""

from __future__ import annotations

import re

import frappe


_WORD_ALNUM = re.compile(r"[^A-Za-z0-9]+")


def _letters(word: str, take: int) -> str:
	"""First `take` alphanumeric characters, uppercased; pad with X."""
	clean = _WORD_ALNUM.sub("", word or "").upper()
	out = clean[:take].ljust(take, "X")
	return out[:take]


def generate_party_code(display_name: str | None, unloco: str | None) -> str:
	"""Build a 9-character code from name tokens and UN/LOCODE link value."""
	text = (display_name or "").strip()
	parts = text.split()
	w1 = parts[0] if parts else ""
	w2 = parts[1] if len(parts) > 1 else ""
	part_a = _letters(w1, 3)
	part_b = _letters(w2, 3) if w2 else "XXX"
	unloc = (unloco or "").strip().upper()
	if len(unloc) >= 3:
		part_c = unloc[-3:]
	else:
		part_c = unloc.ljust(3, "0")[:3]
	return f"{part_a}{part_b}{part_c}"


def ensure_unique_code(
	doctype: str,
	base: str,
	doc_name: str | None,
	code_fieldname: str = "code",
) -> str:
	"""If `base` is already used by another document, replace the last 3 characters with a numeric suffix."""
	candidate = base[:9].ljust(9, "X")[:9]
	seq = 0
	while True:
		found = frappe.db.exists(doctype, {code_fieldname: candidate})
		if not found or found == doc_name:
			return candidate
		seq += 1
		if seq > 999:
			frappe.throw(
				frappe._(
					"Could not allocate a unique {0} after many attempts; adjust the name or UN/LOCODE."
				).format(code_fieldname)
			)
		candidate = candidate[:6] + str(seq).zfill(3)


def maybe_set_party_code(
	doc,
	*,
	name_field: str,
	unloco_field: str,
	code_fieldname: str = "code",
) -> None:
	"""Fill empty party code from display name + UN/LOCODE."""
	existing = (doc.get(code_fieldname) or "").strip()
	if existing:
		return
	name_val = (doc.get(name_field) or "").strip()
	if not name_val:
		return
	unloco = doc.get(unloco_field)
	base = generate_party_code(name_val, unloco)
	doc.set(code_fieldname, ensure_unique_code(doc.doctype, base, doc.name, code_fieldname))


def validate_customer_supplier_party_code(doc, method=None) -> None:
	"""Doc hook: Customer / Supplier custom fields ``logistics_party_code`` and ``logistics_default_unloco``."""
	meta = frappe.get_meta(doc.doctype)
	if not meta.has_field("logistics_party_code"):
		return
	maybe_set_party_code(
		doc,
		name_field="customer_name" if doc.doctype == "Customer" else "supplier_name",
		unloco_field="logistics_default_unloco",
		code_fieldname="logistics_party_code",
	)
