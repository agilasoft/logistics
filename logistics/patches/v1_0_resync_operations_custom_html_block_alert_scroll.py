# Copyright (c) 2026, Agilasoft and contributors
"""Re-sync operations Custom HTML Blocks from fixture (alert body scroll caps in script + style)."""


def execute():
	from logistics.patches.v1_0_ensure_operations_dashboard_custom_html_blocks import execute as sync_blocks

	sync_blocks()
