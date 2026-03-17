# Copyright (c) 2025, www.agilasoft.com and contributors
"""Create default Dimension Volume UOM Conversion records so package volume from dimensions works."""

import frappe


def execute():
    from logistics.warehousing.commands.create_default_volume_uom_conversions import create_default_conversions

    create_default_conversions()
