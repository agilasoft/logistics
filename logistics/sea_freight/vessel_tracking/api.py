# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Deprecated compatibility shim.

Vessel-tracking providers and credentials are owned by **GoConnect Settings**
now. The canonical endpoint is ``goconnect.api.sea.get_vessel_position_for_map``;
this module just forwards to it so any external integration / saved bookmark
that still calls the old logistics path keeps working.
"""

from __future__ import unicode_literals

import frappe
from frappe import _


@frappe.whitelist()
def get_vessel_position_for_map(sea_shipment):
	"""Backward-compatible wrapper around goConnect.

	Forwards to :func:`goconnect.api.sea.get_vessel_position_for_map`. Returns
	a friendly error payload if goConnect is not installed instead of raising,
	so dashboard map overlays degrade gracefully.
	"""
	try:
		installed_apps = frappe.get_installed_apps()
	except Exception:
		installed_apps = []
	if "goconnect" not in installed_apps:
		return {
			"success": False,
			"message": _(
				"Vessel tracking has moved to GoConnect. Install / enable the "
				"goconnect app and configure providers in GoConnect Settings ▸ Vessel."
			),
		}

	from goconnect.api.sea import get_vessel_position_for_map as _gc_get_position

	return _gc_get_position(sea_shipment=sea_shipment)
