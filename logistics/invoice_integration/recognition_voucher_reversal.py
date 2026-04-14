# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared helpers for idempotent WIP / accrual reversal Journal Entries tied to vouchers."""

from __future__ import unicode_literals

import frappe

# Machine-readable suffix on JE user_remark (LOCATE match — no SQL LIKE wildcards).
# ERPNext rejects SI/PI reference_type on rows unless account = invoice receivable/payable,
# so reversal JEs must not set reference on accounts; we key idempotency on this marker instead.
LOGISTICS_REVERSAL_MARKER = "CargoNext|RecognitionReversal|{voucher_type}|{voucher_name}|"


def append_logistics_reversal_marker(user_remark, voucher_type, voucher_name):
	"""Append stable idempotency token to user_remark (human text first, marker last line)."""
	marker = LOGISTICS_REVERSAL_MARKER.format(voucher_type=voucher_type or "", voucher_name=voucher_name or "")
	base = (user_remark or "").rstrip()
	return base + ("\n" if base else "") + marker


def reversal_journal_entry_exists(reference_type, reference_name, user_remark_substring=None):
	"""
	Return name of a submitted Journal Entry that has at least one Account row
	pointing to reference_type/reference_name. Optional user_remark_substring narrows the match.
	"""
	if not reference_type or not reference_name:
		return None
	sql = """
		SELECT DISTINCT je.name
		FROM `tabJournal Entry` je
		INNER JOIN `tabJournal Entry Account` a ON a.parent = je.name AND a.parenttype = 'Journal Entry'
		WHERE je.docstatus = 1
		  AND a.reference_type = %(rt)s AND a.reference_name = %(rn)s
	"""
	params = {"rt": reference_type, "rn": reference_name}
	if user_remark_substring:
		like = user_remark_substring if "%" in user_remark_substring else ("%" + user_remark_substring + "%")
		sql += " AND je.user_remark LIKE %(like)s"
		params["like"] = like
	sql += " LIMIT 1"
	rows = frappe.db.sql(sql, params)
	return rows[0][0] if rows else None


def reversal_journal_entry_exists_for_voucher(voucher_type, voucher_name):
	"""
	Return a submitted JE already posted for this logistics reversal.

	1) Legacy: account rows with reference_type/reference_name = SI/PI (older builds).
	2) Current: user_remark contains LOGISTICS_REVERSAL_MARKER (SI/PI must not be set on rows — ERPNext validate_reference_doc).
	"""
	if not voucher_type or not voucher_name:
		return None
	existing = reversal_journal_entry_exists(voucher_type, voucher_name)
	if existing:
		return existing
	marker = LOGISTICS_REVERSAL_MARKER.format(voucher_type=voucher_type, voucher_name=voucher_name)
	row = frappe.db.sql(
		"""
		SELECT name FROM `tabJournal Entry`
		WHERE docstatus = 1 AND LOCATE(%(m)s, IFNULL(user_remark, '')) > 0
		LIMIT 1
		""",
		{"m": marker},
	)
	return row[0][0] if row else None


def reversal_journal_entry_exists_by_remark_locate(remark_fragment):
	"""Submitted JE whose user_remark contains remark_fragment (substring, LOCATE — safe for special chars)."""
	if not remark_fragment:
		return None
	row = frappe.db.sql(
		"""
		SELECT name FROM `tabJournal Entry`
		WHERE docstatus = 1 AND LOCATE(%(f)s, IFNULL(user_remark, '')) > 0
		LIMIT 1
		""",
		{"f": remark_fragment},
	)
	return row[0][0] if row else None
