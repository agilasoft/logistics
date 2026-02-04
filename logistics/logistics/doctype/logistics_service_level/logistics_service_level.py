# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from typing import Optional

import frappe
from frappe.model.document import Document


class LogisticsServiceLevel(Document):
	pass


def get_sla_settings_for_module(service_level_name: str, module: str) -> Optional[dict]:
	"""
	Get SLA settings from the Service Level by Module child table for the given module.
	Returns dict with sla_target_base_date, sla_transit_days, sla_business_day_end_hour,
	sla_at_risk_hours_before, sla_breach_grace_minutes, or None if no enabled row for that module.
	"""
	if not service_level_name or not module:
		return None
	rows = frappe.get_all(
		"Logistics Service Level Module",
		filters={"parent": service_level_name, "parenttype": "Logistics Service Level", "module": module, "enabled": 1},
		fields=["sla_target_base_date", "sla_transit_days", "sla_business_day_end_hour", "sla_at_risk_hours_before", "sla_breach_grace_minutes"],
		limit=1
	)
	if not rows:
		return None
	return dict(rows[0])
