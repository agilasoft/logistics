# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Show MICE on the desk. Remove every Exhibits tile, including saved layouts."""

from __future__ import annotations

from logistics.mice.desk_icon import sync_desk


def execute():
	sync_desk()
