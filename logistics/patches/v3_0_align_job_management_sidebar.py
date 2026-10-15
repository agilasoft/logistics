# Copyright (c) 2026, Agilasoft and contributors
"""Re-apply the Job Management sidebar after it is aligned to the other modules."""

from __future__ import annotations

from logistics.patches.v3_0_sync_job_management_sidebar import execute as sync_sidebar


def execute():
	sync_sidebar()
