# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""Resolve GL accounts from Item / Item Group defaults with company fallback."""

from __future__ import unicode_literals

from typing import Optional, Tuple

import frappe
from frappe import _

_BASE_DEFAULT_FIELDS = ("income_account", "expense_account", "purchase_expense_account")
_EXTRA_DEFAULT_FIELDS = (
	"custom_wip_account",
	"custom_cost_accrual_account",
	"custom_standard_cost_account",
	"custom_applied_standard_cost_account",
)
_HEADER_STANDARD_COST_FIELDS = (
	"custom_standard_cost_account",
	"custom_applied_standard_cost_account",
)


def _item_default_columns() -> list:
	cols = list(_BASE_DEFAULT_FIELDS)
	for col in _EXTRA_DEFAULT_FIELDS:
		if frappe.db.has_column("Item Default", col):
			cols.append(col)
	return cols


def _item_default_accounts(item_code: str, company: str, parenttype: str, parent: str) -> dict:
	if not parent or not company:
		return {}
	cols = _item_default_columns()
	row = frappe.db.sql(
		"""
		SELECT {cols}
		FROM `tabItem Default`
		WHERE parent=%(parent)s AND parenttype=%(parenttype)s AND company=%(company)s
		LIMIT 1
		""".format(cols=", ".join(cols)),
		{"parent": parent, "parenttype": parenttype, "company": company},
		as_dict=True,
	)
	return row[0] if row else {}


def _group_default_accounts(item_code: str, company: str) -> dict:
	if not item_code or not company:
		return {}
	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if not item_group:
		return {}
	return _item_default_accounts(item_code, company, "Item Group", item_group)


def _first_default_value(item_code: str, company: str, fieldname: str) -> Optional[str]:
	if not item_code or not company or not frappe.db.has_column("Item Default", fieldname):
		return None
	row = _item_default_accounts(item_code, company, "Item", item_code)
	if row.get(fieldname):
		return row.get(fieldname)
	group_row = _group_default_accounts(item_code, company)
	return group_row.get(fieldname) or None


def get_expense_account_for_item(item_code: str, company: str) -> Optional[str]:
	"""Resolve expense account: Item Default -> Item Group Default -> Company default."""
	if not item_code:
		return None

	row = _item_default_accounts(item_code, company, "Item", item_code)
	acc = row.get("expense_account") or row.get("purchase_expense_account")
	if acc:
		return acc

	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		row = _item_default_accounts(item_code, company, "Item Group", item_group)
		acc = row.get("expense_account") or row.get("purchase_expense_account")
		if acc:
			return acc

	co_defaults = frappe.db.get_value(
		"Company",
		company,
		["default_expense_account", "purchase_expense_account"],
		as_dict=True,
	) or {}
	return co_defaults.get("default_expense_account") or co_defaults.get("purchase_expense_account") or None


def get_income_account_for_item(item_code: str, company: str) -> Optional[str]:
	"""Resolve income account: Item Default -> Item Group Default -> Company default."""
	if not item_code:
		return None

	row = _item_default_accounts(item_code, company, "Item", item_code)
	acc = row.get("income_account")
	if acc:
		return acc

	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		row = _item_default_accounts(item_code, company, "Item Group", item_group)
		acc = row.get("income_account")
		if acc:
			return acc

	return frappe.db.get_value("Company", company, "default_income_account") or None


def get_item_accounts_for_internal_billing(item_code: str, company: str) -> Tuple[str, str]:
	"""Return (expense_account, income_account) for internal billing; throw if either is missing."""
	expense_account = get_expense_account_for_item(item_code, company)
	income_account = get_income_account_for_item(item_code, company)
	missing = []
	if not expense_account:
		missing.append(_("expense"))
	if not income_account:
		missing.append(_("income"))
	if missing:
		frappe.throw(
			_("Item {0} (company {1}): set {2} account in Item Defaults for internal billing.").format(
				item_code,
				company,
				" and ".join(missing),
			)
		)
	return expense_account, income_account


def get_wip_account_for_item(item_code: str, company: str, fallback: Optional[str] = None) -> Optional[str]:
	"""WIP income account: Item Default, Item Group Default, then the recognition policy."""
	if not item_code:
		return fallback
	return _first_default_value(item_code, company, "custom_wip_account") or fallback


def get_cost_accrual_account_for_item(
	item_code: str, company: str, fallback: Optional[str] = None
) -> Optional[str]:
	"""Cost accrual expense account: Item Default, Item Group Default, then the recognition policy."""
	if not item_code:
		return fallback
	return _first_default_value(item_code, company, "custom_cost_accrual_account") or fallback


def _item_header_standard_cost(item_code: str) -> dict:
	fields = [fn for fn in _HEADER_STANDARD_COST_FIELDS if frappe.db.has_column("Item", fn)]
	if not item_code or not fields:
		return {}
	return frappe.db.get_value("Item", item_code, fields, as_dict=True) or {}


def get_standard_cost_accounts_for_item(item_code: str, company: str) -> Tuple[Optional[str], Optional[str]]:
	"""Return (standard cost, applied standard cost).

	Each side resolves independently: Item Default, then the Item header, then Item Group Default.
	"""
	if not item_code:
		return None, None
	item_row = _item_default_accounts(item_code, company, "Item", item_code) if company else {}
	header = _item_header_standard_cost(item_code)
	group_row = _group_default_accounts(item_code, company)

	def pick(fieldname: str) -> Optional[str]:
		return item_row.get(fieldname) or header.get(fieldname) or group_row.get(fieldname) or None

	return pick("custom_standard_cost_account"), pick("custom_applied_standard_cost_account")


def validate_item_default_accounts(doc, method=None):
	"""WIP, Accrual, and standard-cost accounts on Item / Item Group defaults must match the row company."""
	rows = doc.get("item_defaults") or []
	if not rows:
		return
	if not frappe.get_meta("Item Default").get_field("custom_wip_account"):
		return
	for row in rows:
		_validate_role_account(row, "custom_wip_account", _("WIP Account"), "Income Account", "WIP")
		_validate_role_account(
			row, "custom_cost_accrual_account", _("Accrual Account"), "Expense Account", "Accrual"
		)
		_validate_leaf_account(row, "custom_standard_cost_account", _("Standard Cost Account"))
		_validate_leaf_account(row, "custom_applied_standard_cost_account", _("Applied Standard Cost Account"))


def _account_for_validation(name: str):
	fields = ["company", "account_type", "is_group"]
	if frappe.db.has_column("Account", "job_profit_account_type"):
		fields.append("job_profit_account_type")
	return frappe.db.get_value("Account", name, fields, as_dict=True)


def _validate_role_account(row, fieldname, label, account_type, job_profit):
	acc = row.get(fieldname)
	if not acc:
		return
	ac = _account_for_validation(acc)
	if not ac:
		frappe.throw(_("{0} {1} does not exist.").format(label, acc))
	_validate_account_company(row, ac, acc, label)
	if ac.get("is_group"):
		frappe.throw(_("{0} {1} cannot be a group account.").format(label, acc))
	if (ac.get("account_type") or "") != account_type:
		frappe.throw(_("{0} must be an {1}.").format(label, account_type))
	if frappe.db.has_column("Account", "job_profit_account_type"):
		jpt = (ac.get("job_profit_account_type") or "").strip()
		if jpt != job_profit:
			frappe.throw(_("{0}: Job Profit Account Type must be {1}.").format(label, job_profit))


def _validate_leaf_account(row, fieldname, label):
	acc = row.get(fieldname)
	if not acc:
		return
	ac = _account_for_validation(acc)
	if not ac:
		frappe.throw(_("{0} {1} does not exist.").format(label, acc))
	_validate_account_company(row, ac, acc, label)
	if ac.get("is_group"):
		frappe.throw(_("{0} {1} cannot be a group account.").format(label, acc))


def _validate_account_company(row, ac, acc, label):
	company = row.get("company")
	if not company:
		frappe.throw(_("{0} requires a Company on the Item Default row.").format(label))
	if ac.get("company") != company:
		frappe.throw(_("{0} {1} must belong to company {2}.").format(label, acc, company))


def item_default_gl_fields() -> list:
	"""Account link fields on Item Default, including purchase expense when it is not a Link."""
	fields = []
	meta = frappe.get_meta("Item Default")
	for df in getattr(meta, "fields", None) or []:
		fieldname = df.get("fieldname")
		if df.get("fieldtype") == "Link" and df.get("options") == "Account" and fieldname:
			if frappe.db.has_column("Item Default", fieldname):
				fields.append(fieldname)
	if not fields:
		for fieldname in list(_BASE_DEFAULT_FIELDS) + list(_EXTRA_DEFAULT_FIELDS):
			if frappe.db.has_column("Item Default", fieldname) and fieldname not in fields:
				fields.append(fieldname)
	if frappe.db.has_column("Item Default", "purchase_expense_account") and "purchase_expense_account" not in fields:
		fields.append("purchase_expense_account")
	return fields


def accounts_by_company(rows, fields) -> dict:
	"""Non-empty account values from Item Default rows, merged per company."""
	by_company = {}
	for row in rows or []:
		company = row.get("company")
		if not company:
			continue
		values = {field: row.get(field) for field in fields if row.get(field)}
		if not values:
			continue
		by_company.setdefault(company, {}).update(values)
	return by_company


def copy_company_accounts(item, company_accounts) -> bool:
	"""Copy non-empty company accounts onto item defaults. Blank source fields are left as they are."""
	changed = False
	rows = list(item.get("item_defaults") or [])
	for company, values in (company_accounts or {}).items():
		if not company or not values:
			continue
		row = next((existing for existing in rows if existing.get("company") == company), None)
		if row is None:
			row = item.append("item_defaults", {"company": company})
			rows.append(row)
			changed = True
		for field, value in values.items():
			if not value or row.get(field) == value:
				continue
			if hasattr(row, "set"):
				row.set(field, value)
			else:
				row[field] = value
			changed = True
	return changed


def item_groups_including_descendants(item_group: str) -> list:
	bounds = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True) or {}
	lft = bounds.get("lft") if isinstance(bounds, dict) else None
	rgt = bounds.get("rgt") if isinstance(bounds, dict) else None
	if lft is None or rgt is None:
		return [item_group]
	rows = frappe.db.sql(
		"""
		SELECT name FROM `tabItem Group`
		WHERE lft >= %(lft)s AND rgt <= %(rgt)s
		ORDER BY lft
		""",
		{"lft": lft, "rgt": rgt},
	)
	names = []
	for row in rows or []:
		names.append(row.get("name") if isinstance(row, dict) else row[0])
	return [name for name in names if name] or [item_group]


@frappe.whitelist()
def apply_gl_accounts_to_items(item_group):
	"""Copy this Item Group's GL accounts onto every Item in the group and its child groups."""
	if not item_group:
		frappe.throw(_("Item Group is required."))
	if not frappe.db.exists("Item Group", item_group):
		frappe.throw(_("Item Group {0} does not exist.").format(item_group))
	frappe.has_permission("Item Group", "read", doc=item_group, throw=True)
	frappe.has_permission("Item", "write", throw=True)

	group = frappe.get_doc("Item Group", item_group)
	fields = item_default_gl_fields()
	company_accounts = accounts_by_company(group.get("item_defaults") or [], fields)
	if not company_accounts:
		frappe.throw(_("Set GL accounts on Item Defaults for at least one company."))

	groups = item_groups_including_descendants(item_group)
	item_rows = frappe.get_all("Item", filters={"item_group": ["in", groups]}, fields=["name"])
	item_names = []
	for row in item_rows or []:
		item_names.append(row.get("name") if isinstance(row, dict) else row)
	updated = 0
	for name in item_names:
		item = frappe.get_doc("Item", name)
		if copy_company_accounts(item, company_accounts):
			item.save()
			updated += 1
	return {"items": len(item_names), "updated": updated, "companies": list(company_accounts)}
