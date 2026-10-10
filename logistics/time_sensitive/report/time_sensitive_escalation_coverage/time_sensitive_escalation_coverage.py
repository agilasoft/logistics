# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Setup: which case types have an enabled escalation rule, and which do not."""

from frappe import _
from frappe.utils import cint

from logistics.analytics_reports.bootstrap import tally_chart
from logistics.time_sensitive.ts_reports import (
	escalation_coverage_rows,
	fetch_case_types,
	fetch_escalation_rules,
)


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	case_types = fetch_case_types()
	if cint(filters.get("enabled_only")):
		case_types = [row for row in case_types if cint(row.get("enabled"))]
	if filters.get("case_type"):
		case_types = [row for row in case_types if row.get("name") == filters.get("case_type")]
	rules = fetch_escalation_rules()
	rows = escalation_coverage_rows(case_types, rules)
	if filters.get("covered"):
		rows = [row for row in rows if row.get("covered") == filters.get("covered")]
	chart = tally_chart(rows, "covered", dataset_label=_("Case Types"))
	enabled_rules = sum(1 for rule in rules if cint(rule.get("enabled")))
	return columns, rows, None, chart, _summary(rows, enabled_rules)


def _columns():
	return [
		{
			"label": _("Case Type"),
			"fieldname": "case_type",
			"fieldtype": "Link",
			"options": "Time Sensitive Case Type",
			"width": 140,
		},
		{"label": _("Name"), "fieldname": "case_type_name", "fieldtype": "Data", "width": 180},
		{"label": _("Type Enabled"), "fieldname": "type_enabled", "fieldtype": "Data", "width": 110},
		{"label": _("Covered"), "fieldname": "covered", "fieldtype": "Data", "width": 90},
		{"label": _("Enabled Rules"), "fieldname": "enabled_rules", "fieldtype": "Int", "width": 120},
		{"label": _("Triggers"), "fieldname": "triggers", "fieldtype": "Data", "width": 220},
		{"label": _("Escalate To"), "fieldname": "escalate_to", "fieldtype": "Data", "width": 180},
	]


def _summary(rows, enabled_rules):
	uncovered = sum(1 for row in rows if row.get("covered") != "Yes")
	return [
		{"label": _("Case Types"), "value": len(rows), "indicator": "blue"},
		{"label": _("Uncovered"), "value": uncovered, "indicator": "red" if uncovered else "green"},
		{"label": _("Enabled Rules"), "value": enabled_rules, "indicator": "blue"},
	]
