# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Re-run lifecycle job_no repair using Lifecycle Job documents (v1_21 used plain dicts)."""

from __future__ import annotations

import frappe

from logistics.patches.v1_21_fix_lifecycle_job_no_order_duplicate import execute as _repair_execute


def execute():
	_repair_execute()
