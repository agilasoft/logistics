# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Virtualize ``internal_job_details`` on all operational booking/order/shipment/job parents.

``Sea Booking`` / ``Sea Shipment`` may already have been migrated by
``v3_0_virtualize_sea_internal_job_details``; this patch is idempotent for those types.
"""

from __future__ import annotations

import frappe

from logistics.patches.v3_0_virtualize_sea_internal_job_details import execute as _migrate_parents

# Re-use the Sea migration implementation (same parent/field map expanded in-module).
execute = _migrate_parents
