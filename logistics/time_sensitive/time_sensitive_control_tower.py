# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Time Sensitive Control Tower number cards."""

from __future__ import unicode_literals

import frappe

from logistics.control_tower.module_tower import number_card_value as _number_card_value


@frappe.whitelist()
def number_card_value(filters=None):
	"""Custom Number Card value for the Time Sensitive Control Tower dashboard."""
	return _number_card_value('time_sensitive', filters)
