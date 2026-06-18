# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Restore programme charge estimated revenue/cost from Sales Quote (plan vs actual)."""

from __future__ import annotations

import frappe

from logistics.special_projects.special_project_charge_execution import (
	_recalculate_programme_charge,
	reconcile_programme_charge_qty_from_execution_logs,
)
from logistics.utils.sales_quote_programme_charges import (
	restore_programme_charge_estimates_from_sales_quote,
)


def execute():
	if not frappe.db.table_exists("tabSpecial Project"):
		return

	for name in frappe.get_all("Special Project", pluck="name"):
		sp_doc = frappe.get_doc("Special Project", name)
		if not getattr(sp_doc, "sales_quote", None) and not sp_doc.get("charges"):
			continue
		restore_programme_charge_estimates_from_sales_quote(sp_doc)
		if sp_doc.get("charge_execution_logs"):
			reconcile_programme_charge_qty_from_execution_logs(sp_doc)
		else:
			for charge in sp_doc.get("charges") or []:
				_recalculate_programme_charge(charge, sp_doc)
		sp_doc.flags.ignore_validate = True
		sp_doc.flags.ignore_charges_sync = True
		sp_doc.save(ignore_permissions=True)

	frappe.db.commit()
