# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Remove Air Shipment tracking columns after DocType model synchronization.

The pre-model patch creates enough room for the Air Shipment ALTER. Frappe can
temporarily recreate legacy columns from the database metadata it loaded before
that sync, so this post-model pass performs the final idempotent cleanup.
"""

from logistics.patches.v3_0_drop_air_shipment_tracking_fields import execute

