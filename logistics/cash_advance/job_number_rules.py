# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

from typing import Optional

import frappe
from frappe.utils import cint


def get_item_require_job_number(item_code: Optional[str]) -> bool:
	if not item_code:
		return False
	return bool(cint(frappe.db.get_value("Item", item_code, "require_job_number")))


def row_requires_job_number(require_job_number_flag, item_code: Optional[str]) -> bool:
	return bool(cint(require_job_number_flag)) and get_item_require_job_number(item_code)


def resolve_row_job_number(parent_job_number: Optional[str], row) -> Optional[str]:
	row_job_number = getattr(row, "job_number", None)
	if row_job_number:
		return row_job_number
	return parent_job_number
