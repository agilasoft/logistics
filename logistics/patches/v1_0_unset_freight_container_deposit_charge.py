# -*- coding: utf-8 -*-
"""Unset Container Deposit Charge on FREIGHT — sea freight cost item, not a container deposit."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.has_column("Item", "custom_container_deposit_charge"):
		return
	if not frappe.db.exists("Item", "FREIGHT"):
		return
	if not frappe.db.get_value("Item", "FREIGHT", "custom_container_deposit_charge"):
		return
	frappe.db.set_value("Item", "FREIGHT", "custom_container_deposit_charge", 0, update_modified=False)
