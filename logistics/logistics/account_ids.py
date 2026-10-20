# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rebuild Account document IDs from the current account name.

ERPNext stores the ID as ``{account_number} - {account_name} - {abbr}`` when
the account has a number, and ``{account_name} - {abbr}`` otherwise
(``erpnext.accounts.utils.get_autoname_with_number``). Changing Account Name
on its own leaves the ID behind. This module plans those renames and applies
them through ``frappe.rename_doc`` so linked records follow.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

NAME_LENGTH = 140
_TEMP_PREFIX = "__ren__"


def expected_account_id(account_number, account_name, company_abbr):
	"""Return the Account ID for the current naming rule, or None when it cannot be built."""
	title = (account_name or "").strip()
	if not title or company_abbr is None or company_abbr == "":
		return None
	number = str(account_number).strip() if account_number is not None else ""
	parts = [title, company_abbr]
	if number:
		parts.insert(0, number)
	return " - ".join(parts)


def plan_account_id_updates(accounts, name_length=NAME_LENGTH):
	"""Plan ID updates for account rows.

	Each row needs ``name``, ``account_name``, ``account_number``, and
	``company_abbr``. Rows that already match are omitted. ``skipped`` covers
	rows that need a new ID but cannot get one. ``collisions`` covers a new ID
	that another account still holds, or two accounts that would share an ID.
	"""
	rows = []
	seen = set()
	for row in accounts or []:
		name = row.get("name")
		if not name or name in seen:
			continue
		seen.add(name)
		rows.append(row)

	current_names = {row["name"] for row in rows}
	current_by_fold = {}
	for name in current_names:
		current_by_fold.setdefault(name.casefold(), name)

	updates_by_old = {}
	skipped = []
	for row in rows:
		new_name = expected_account_id(row.get("account_number"), row.get("account_name"), row.get("company_abbr"))
		if new_name is None:
			skipped.append({"name": row["name"], "reason": "missing"})
			continue
		if len(new_name) > name_length:
			skipped.append({"name": row["name"], "reason": "too_long", "new_name": new_name})
			continue
		if new_name == row["name"]:
			continue
		updates_by_old[row["name"]] = new_name

	moving = set(updates_by_old)
	target_groups = defaultdict(list)
	for old, new in updates_by_old.items():
		target_groups[new.casefold()].append({"from": old, "to": new})

	updates = []
	collisions = []
	for pairs in target_groups.values():
		if len(pairs) > 1:
			collisions.append(
				{
					"from": pairs[0]["from"],
					"to": pairs[0]["to"],
					"existing": ", ".join(pair["from"] for pair in pairs[1:]),
					"reason": "duplicate",
				}
			)
			continue
		pair = pairs[0]
		occupant = current_by_fold.get(pair["to"].casefold())
		if occupant and occupant != pair["from"] and occupant not in moving:
			collisions.append({**pair, "existing": occupant, "reason": "occupied"})
			continue
		updates.append(pair)

	updates.sort(key=lambda item: item["from"])
	collisions.sort(key=lambda item: item["from"])
	skipped.sort(key=lambda item: item["name"])
	return {"updates": updates, "skipped": skipped, "collisions": collisions}


def temporary_account_id(seed, used, name_length=NAME_LENGTH):
	"""Return a short unused ID that can hold an account during a swap."""
	digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
	width = 12
	for start in range(0, len(digest) - width + 1):
		candidate = f"{_TEMP_PREFIX}{digest[start : start + width]}"
		if len(candidate) <= name_length and candidate not in used:
			return candidate
	raise ValueError(f"Could not allocate a temporary ID for {seed}")


def apply_account_id_updates(updates, rename, taken_names, name_length=NAME_LENGTH):
	"""Rename accounts to their new IDs.

	Renames go through a temporary ID first so two accounts can exchange names
	without tripping the unique ID. ``rename(old, new)`` performs one rename.
	"""
	if not updates:
		return []
	used = set(taken_names or [])
	for item in updates:
		used.add(item["to"])
	staged = []
	for item in updates:
		temp = temporary_account_id(item["from"], used, name_length=name_length)
		used.add(temp)
		staged.append((item["from"], temp, item["to"]))
	for old, temp, _new in staged:
		rename(old, temp)
	for _old, temp, new in staged:
		rename(temp, new)
	return [{"from": old, "to": new} for old, _temp, new in staged]


def update_account_ids(company=None, apply=0):
	"""Preview or apply Account ID updates.

	Pass ``apply`` truthy to rename. The response lists ``updates`` (or
	``renamed``), ``skipped``, and ``collisions``.
	"""
	import frappe
	from frappe import _
	from frappe.utils import cint

	if not frappe.has_permission("Account", "write"):
		frappe.throw(_("Not permitted to update Account IDs"), frappe.PermissionError)

	company = (company or "").strip()
	if company and not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} does not exist").format(company))

	rows = _account_rows(company)
	abbrs = _company_abbreviations({row.company for row in rows if row.company})
	plan = plan_account_id_updates(
		[
			{
				"name": row.name,
				"account_name": row.account_name,
				"account_number": row.account_number,
				"company_abbr": abbrs.get(row.company),
			}
			for row in rows
		],
		name_length=_account_id_length(),
	)
	result = {
		"updates": plan["updates"],
		"skipped": plan["skipped"],
		"collisions": plan["collisions"],
		"renamed": [],
	}
	if not cint(apply):
		return result
	if plan["collisions"]:
		_throw_collisions(plan["collisions"])
	if not plan["updates"]:
		return result

	_ensure_gl_idle()

	def rename(old, new):
		frappe.rename_doc("Account", old, new, force=True)

	result["renamed"] = apply_account_id_updates(
		plan["updates"],
		rename,
		[row.name for row in rows],
		name_length=_account_id_length(),
	)
	result["updates"] = result["renamed"]
	return result


def _account_rows(company):
	import frappe

	filters = {"company": company} if company else {}
	rows = []
	page = 500
	start = 0
	while True:
		chunk = frappe.get_list(
			"Account",
			filters=filters,
			fields=["name", "account_name", "account_number", "company"],
			order_by="name asc",
			limit_start=start,
			limit_page_length=page,
		)
		rows.extend(chunk)
		if len(chunk) < page:
			return rows
		start += page


def _company_abbreviations(companies):
	import frappe

	if not companies:
		return {}
	records = frappe.get_all(
		"Company",
		filters={"name": ["in", list(companies)]},
		fields=["name", "abbr"],
		limit_page_length=0,
	)
	return {record.name: record.abbr for record in records}


def _account_id_length():
	import frappe

	row = frappe.db.sql(
		"""
		select CHARACTER_MAXIMUM_LENGTH
		from information_schema.COLUMNS
		where TABLE_SCHEMA = DATABASE()
			and TABLE_NAME = 'tabAccount'
			and COLUMN_NAME = 'name'
		"""
	)
	if row and row[0][0]:
		return int(row[0][0])
	return NAME_LENGTH


def _ensure_gl_idle():
	from erpnext.accounts.doctype.account.account import _ensure_idle_system

	_ensure_idle_system()


def _collision_line(item):
	from frappe import _

	if item.get("reason") == "duplicate":
		return _("{0} and {1} would both become {2}").format(item["from"], item["existing"], item["to"])
	return _("{0} would become {1}, already used by {2}").format(item["from"], item["to"], item["existing"])


def _throw_collisions(collisions):
	import frappe
	from frappe import _

	lines = [_collision_line(item) for item in collisions[:20]]
	if len(collisions) > 20:
		lines.append(_("And {0} more.").format(len(collisions) - 20))
	frappe.throw("<br>".join(lines), title=_("Account ID already exists"))


def _register_whitelist():
	import frappe

	globals()["update_account_ids"] = frappe.whitelist()(update_account_ids)


try:
	_register_whitelist()
except ModuleNotFoundError:
	pass
