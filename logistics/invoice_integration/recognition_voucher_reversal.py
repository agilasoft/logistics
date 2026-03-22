# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared helpers for idempotent WIP / accrual reversal Journal Entries tied to vouchers."""

from __future__ import unicode_literals

import frappe


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
