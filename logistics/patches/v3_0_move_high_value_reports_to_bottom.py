# Copyright (c) 2026, Agilasoft and contributors
"""Place High Value Reports and Analytics cards at the bottom of the workspace."""

from logistics.patches.v3_0_sync_high_value_reports_workspace import execute as sync_reports_workspace


def execute():
	sync_reports_workspace()
