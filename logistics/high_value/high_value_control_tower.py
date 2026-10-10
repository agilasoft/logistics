# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""High Value Control Tower number cards."""

from __future__ import unicode_literals

import frappe

from logistics.control_tower.module_tower import number_card_value as _number_card_value


@frappe.whitelist()
def number_card_value(filters=None):
	"""Custom Number Card value for the High Value Control Tower dashboard."""
	return _number_card_value('high_value', filters)
