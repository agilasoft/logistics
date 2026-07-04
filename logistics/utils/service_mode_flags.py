# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Module flags on Load Type / Transport Mode / Freight Agent masters vs charge service types."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage

MODULE_FLAG_FIELDS = ("air", "sea", "transport", "customs", "warehousing")
SERVICE_MODE_MASTER_DOCTYPES = ("Load Type", "Transport Mode", "Freight Agent")

SERVICE_TYPE_TO_MODULE_FLAG = {
	"air": "air",
	"sea": "sea",
	"transport": "transport",
	"custom": "customs",
	"warehousing": "warehousing",
}


def module_flag_for_charge_service_type(value: Any) -> str | None:
	"""Return Load Type / Transport Mode checkbox field for a service type label."""
	c = canonical_charge_service_type_for_storage(value)
	if not c:
		return None
	return SERVICE_TYPE_TO_MODULE_FLAG.get(c)


def get_service_mode_flags_bulk(master_doctype: str, names: list | str | None) -> dict:
	"""Return module flags for Load Type, Transport Mode, or Freight Agent names (desk sanitization)."""
	if master_doctype not in SERVICE_MODE_MASTER_DOCTYPES:
		return {}
	if isinstance(names, str):
		names = json.loads(names)
	if not names:
		return {}
	out = {}
	for name in names:
		if not name:
			continue
		row = frappe.db.get_value(
			master_doctype,
			name,
			list(MODULE_FLAG_FIELDS),
			as_dict=True,
		)
		if row:
			out[name] = row
	return out


def validate_service_mode_link(
	master_doctype: str,
	mode_name: str | None,
	service_type_label: str | None,
	*,
	context: str,
) -> None:
	"""Raise when a Load Type / Transport Mode / Freight Agent is incompatible with the service type."""
	if master_doctype not in SERVICE_MODE_MASTER_DOCTYPES:
		return
	if not mode_name:
		return
	field = module_flag_for_charge_service_type(service_type_label)
	if not field:
		return
	if not frappe.db.exists(master_doctype, mode_name):
		return
	if frappe.db.get_value(master_doctype, mode_name, field):
		return
	frappe.throw(
		_("{0} '{1}' is not valid for {2}. Select a {0} with '{3}' enabled.").format(
			master_doctype,
			mode_name,
			context,
			service_type_label,
		),
		title=_("Invalid {0}").format(master_doctype),
	)
