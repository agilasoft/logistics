# Copyright (c) 2025, Logistics and contributors
"""Post-migrate: merge Recognition Policy Settings per company and copy legacy fields to child rows."""

import frappe


def after_migrate():
	if not frappe.db.table_exists("tabRecognition Policy Parameter"):
		return

	try:
		_run_recognition_policy_migration()
	except Exception as e:
		frappe.log_error(
			title="Recognition Policy migration",
			message=frappe.get_traceback_with_context(),
		)


def _run_recognition_policy_migration():
	"""One policy doc per company; legacy header -> parameter rows."""
	all_names = frappe.get_all("Recognition Policy Settings", pluck="name")
	if not all_names:
		return

	by_company = {}
	for name in all_names:
		co = frappe.db.get_value("Recognition Policy Settings", name, "company")
		if not co:
			continue
		by_company.setdefault(co, []).append(name)

	for company, names in by_company.items():
		names = sorted(
			names,
			key=lambda n: (
				0 if frappe.db.get_value("Recognition Policy Settings", n, "wip_account") else 1,
				n,
			),
		)
		if len(names) == 1:
			doc = frappe.get_doc("Recognition Policy Settings", names[0])
			_migrate_doc_to_parameters(doc)
			continue

		survivor_name = names[0]
		survivor = frappe.get_doc("Recognition Policy Settings", survivor_name)
		for n in names:
			d = frappe.get_doc("Recognition Policy Settings", n)
			row = _legacy_as_parameter_row(d)
			if row:
				survivor.append("recognition_parameters", row)
		for n in names[1:]:
			try:
				frappe.delete_doc("Recognition Policy Settings", n, force=True, ignore_permissions=True)
			except Exception:
				pass
		survivor.flags.ignore_validate = True
		try:
			survivor.save(ignore_permissions=True)
		except Exception:
			survivor.flags.ignore_validate = False
			raise
		survivor.flags.ignore_validate = False
		_migrate_doc_to_parameters(frappe.get_doc("Recognition Policy Settings", survivor.name))


def _legacy_as_parameter_row(d):
	"""Build child row dict from a policy doc's legacy header fields."""
	if not (
		d.get("wip_account")
		and d.get("revenue_liability_account")
		and d.get("cost_accrual_account")
		and d.get("accrued_cost_liability_account")
	):
		return None
	return {
		"priority": d.get("priority") or 0,
		"branch": d.get("branch"),
		"profit_center": d.get("profit_center"),
		"cost_center": d.get("cost_center"),
		"direction": None,
		"transport_mode": None,
		"recognition_date_basis": d.get("recognition_date_basis")
		or d.get("wip_recognition_date_basis")
		or d.get("accrual_recognition_date_basis")
		or "Job Booking Date",
		"wip_account": d.wip_account,
		"revenue_liability_account": d.revenue_liability_account,
		"cost_accrual_account": d.cost_accrual_account,
		"accrued_cost_liability_account": d.accrued_cost_liability_account,
	}


def _migrate_doc_to_parameters(doc):
	if doc.recognition_parameters:
		return
	row = _legacy_as_parameter_row(doc)
	if not row:
		return
	doc.append("recognition_parameters", row)
	doc.flags.ignore_validate = True
	try:
		doc.save(ignore_permissions=True)
	except Exception:
		doc.flags.ignore_validate = False
		raise
	doc.flags.ignore_validate = False
