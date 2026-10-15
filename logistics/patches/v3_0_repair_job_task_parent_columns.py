# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Job Task parent columns again.

``v3_0_add_job_task_child_columns`` called ``table_exists("tabJob Task")``.
Frappe prefixes ``tab`` itself, so that looked up ``tabtabJob Task``, recorded
success, and left ``tabJob Task`` without ``parent``. Opening Inbound Order
WIN00000016 (and the other warehousing documents that share this checklist)
still fails with unknown column ``parent``. This patch runs the corrected repair.
"""

from __future__ import annotations


def execute():
	from logistics.patches.v3_0_add_job_task_child_columns import execute as repair

	repair()
