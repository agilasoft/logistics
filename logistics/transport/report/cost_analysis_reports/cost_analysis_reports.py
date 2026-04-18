# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from logistics.analytics_reports.bootstrap import run_named_analytics


def execute(filters=None):
	return run_named_analytics("Transport Job", "time:week", filters)
