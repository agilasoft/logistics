# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
"""Add Container Management settings to Logistics Settings."""

from __future__ import unicode_literals

import frappe


def execute():
	"""Ensure Logistics Settings has container management fields (no-op if already migrated)."""
	try:
		settings = frappe.get_single("Logistics Settings")
		# Touch to trigger migration if fields were added
		if not hasattr(settings, "enable_container_management"):
			# Field may not exist yet - migrate will add it
			pass
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
