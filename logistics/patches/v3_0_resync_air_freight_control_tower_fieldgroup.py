# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Re-sync Air Freight Control Tower page script (FieldGroup filters + modern cards)."""

from __future__ import unicode_literals

from logistics.patches.v3_0_sync_air_freight_control_tower_page import execute as _sync


def execute():
	_sync()
