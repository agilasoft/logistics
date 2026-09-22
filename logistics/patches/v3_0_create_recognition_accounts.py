# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create the ASL recognition accounts on every operating company.

Sample (ALL SYSTEMS LOGISTICS INC.):

- WIP Account: WIP Revenue
- Revenue Liability Account: WIP Revenue Liability
- Cost Accrual Account: Accrual Cost
- Accrued Cost Liability Account: Accrued Cost Liability

Existing accounts are left in place. Recognition Policy Settings rows are
filled only where an account field is still empty.
"""

import frappe

COMPANIES = (
	"ALL SYSTEMS LOGISTICS INC.",
	"PRIME WAREHOUSE DYNAMICS CORP.",
	"ALL TRANSPORT NETWORK, INC.",
	"MTE PROPERTIES, INC.",
	"ALTA GLOBAL SERVICES, INC",
	"THE PEAK ONE HOLDINGS INC.",
	"PRIME ALTA HOLDINGS, INC.",
	"PRIME HUB BUSINESS SERVICES",
	"ALTA FAIRS AND EXHIBITS CORP.",
	"FAST PRIME TRANSPORT CORP.",
)

# Parent names are used only when no company already has this ledger.
# On atndemo, ASL already has the four accounts, so other companies follow that parent.
SPECS = (
	{
		"account_name": "WIP Revenue",
		"account_type": "Income Account",
		"job_profit_account_type": "WIP",
		"root_type": "Income",
		"parent_names": ("Service Revenue", "Direct Income", "Revenue", "Income"),
		"policy_field": "wip_account",
	},
	{
		"account_name": "WIP Revenue Liability",
		"account_type": None,
		"job_profit_account_type": None,
		"root_type": "Asset",
		"parent_names": ("Current Assets", "Assets"),
		"policy_field": "revenue_liability_account",
	},
	{
		"account_name": "Accrual Cost",
		"account_type": "Expense Account",
		"job_profit_account_type": "Accrual",
		"root_type": "Expense",
		"parent_names": ("Cost Of Services", "Direct Expenses", "Cost", "Expenses"),
		"policy_field": "cost_accrual_account",
	},
	{
		"account_name": "Accrued Cost Liability",
		"account_type": None,
		"job_profit_account_type": None,
		"root_type": "Liability",
		"parent_names": ("Current Liabilities", "Liabilities"),
		"policy_field": "accrued_cost_liability_account",
	},
)


def execute():
	if not frappe.db.exists("DocType", "Account"):
		return
	skipped = []
	for company in COMPANIES:
		if not frappe.db.exists("Company", company):
			continue
		try:
			_ensure_company(company, skipped)
		except Exception:
			skipped.append(f"{company}: {frappe.get_traceback()}")
	if skipped:
		print("recognition accounts skipped:\n" + "\n".join(skipped))


def _ensure_company(company, skipped):
	if not frappe.db.exists("Account", {"company": company, "is_group": 1}):
		skipped.append(f"{company}: no chart of accounts")
		return
	accounts = {}
	for spec in SPECS:
		name = _ensure_account(company, spec)
		if not name:
			skipped.append(f"{company}: {spec['account_name']}")
			return
		accounts[spec["policy_field"]] = name
	_ensure_policy(company, accounts)


def _ensure_account(company, spec):
	frappe.flags.recognition_account_created = 0
	existing = frappe.db.get_value(
		"Account",
		{"account_name": spec["account_name"], "company": company, "is_group": 0},
		"name",
	)
	if existing:
		_ensure_job_profit(existing, spec)
		return existing

	parent, account_type, job_profit = _template(company, spec)
	if not parent:
		return None

	doc = frappe.new_doc("Account")
	doc.account_name = spec["account_name"]
	doc.company = company
	doc.parent_account = parent
	doc.is_group = 0
	if account_type:
		doc.account_type = account_type
	if job_profit and _has_job_profit():
		doc.job_profit_account_type = job_profit
	doc.insert(ignore_permissions=True)
	frappe.flags.recognition_account_created = 1
	return doc.name


def _template(company, spec):
	"""Parent and types from an existing ledger of the same name, else chart fallbacks."""
	parent_account_name = None
	account_type = spec["account_type"]
	job_profit = spec["job_profit_account_type"]
	rows = frappe.db.sql(
		"""
		select name, parent_account, account_type
		from tabAccount
		where account_name = %s and is_group = 0 and ifnull(parent_account, '') != ''
		""",
		spec["account_name"],
		as_dict=True,
	)
	if rows and _has_job_profit():
		for row in rows:
			row.job_profit_account_type = frappe.db.get_value(
				"Account", row.name, "job_profit_account_type"
			)
	# Prefer the ASL sample when it exists.
	rows.sort(key=lambda row: 0 if (row.parent_account or "").endswith(" - ASL") else 1)
	if rows:
		parent_account_name = frappe.db.get_value("Account", rows[0].parent_account, "account_name")
		if rows[0].account_type:
			account_type = rows[0].account_type
		if getattr(rows[0], "job_profit_account_type", None):
			job_profit = rows[0].job_profit_account_type

	parent = None
	if parent_account_name:
		parent = frappe.db.get_value(
			"Account",
			{"account_name": parent_account_name, "company": company, "is_group": 1},
			"name",
		)
	if not parent:
		for account_name in spec["parent_names"]:
			parent = frappe.db.get_value(
				"Account",
				{
					"account_name": account_name,
					"company": company,
					"is_group": 1,
					"root_type": spec["root_type"],
				},
				"name",
			)
			if parent:
				break
	if not parent:
		parent = _any_group(company, spec["root_type"])
	return parent, account_type, job_profit


def _any_group(company, root_type):
	"""Any group of this root type. Prefer a subgroup over the chart root."""
	names = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 1, "root_type": root_type},
		fields=["name", "parent_account"],
		limit=50,
	)
	for row in names:
		if row.parent_account:
			return row.name
	if names:
		return names[0].name
	return None


def _ensure_job_profit(account_name, spec):
	wanted = spec["job_profit_account_type"]
	if not wanted or not _has_job_profit():
		return
	current = (frappe.db.get_value("Account", account_name, "job_profit_account_type") or "").strip()
	if current == wanted:
		return
	if current:
		return
	frappe.db.set_value("Account", account_name, "job_profit_account_type", wanted, update_modified=False)


def _ensure_policy(company, accounts):
	if not frappe.db.exists("DocType", "Recognition Policy Settings"):
		return
	name = frappe.db.get_value("Recognition Policy Settings", {"company": company}, "name")
	if not name:
		doc = frappe.new_doc("Recognition Policy Settings")
		doc.company = company
		doc.enabled = 1
		doc.append(
			"recognition_parameters",
			{"recognition_date_basis": "Job Booking Date", **accounts},
		)
		doc.insert(ignore_permissions=True)
		return

	doc = frappe.get_doc("Recognition Policy Settings", name)
	changed = False
	if not doc.recognition_parameters:
		doc.append(
			"recognition_parameters",
			{"recognition_date_basis": "Job Booking Date", **accounts},
		)
		changed = True
	else:
		for row in doc.recognition_parameters:
			for field, account in accounts.items():
				# WIP and Cost Accrual must be the per-company ledgers (WIP Revenue / Accrual Cost).
				# The other two stay as they are once set.
				if field in ("wip_account", "cost_accrual_account") or not row.get(field):
					if row.get(field) != account:
						row.set(field, account)
						changed = True
	if changed:
		doc.save(ignore_permissions=True)


def _has_job_profit():
	return frappe.db.has_column("Account", "job_profit_account_type")
