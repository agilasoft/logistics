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


def needs_temporary_ids(updates):
	"""True when a new ID is still the current ID of an account being renamed."""
	moving = {item["from"].casefold() for item in updates or []}
	return any(item["to"].casefold() in moving for item in updates or [])


def apply_account_id_updates(updates, rename, taken_names, name_length=NAME_LENGTH, commit=None):
	"""Rename accounts to their new IDs.

	A new ID that is free is applied directly. When two accounts would exchange
	IDs, the rename goes through a temporary ID first. ``commit`` runs after
	each rename so a long chart does not stay in one transaction.
	"""
	if not updates:
		return []

	def after_rename():
		if commit:
			commit()

	if not needs_temporary_ids(updates):
		for item in updates:
			rename(item["from"], item["to"])
			after_rename()
		return [{"from": item["from"], "to": item["to"]} for item in updates]

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
		after_rename()
	for _old, temp, new in staged:
		rename(temp, new)
		after_rename()
	return [{"from": old, "to": new} for old, _temp, new in staged]


JOB_TIMEOUT = 4 * 60 * 60


def account_id_job_id(company=None):
	# One rename job at a time. A second company would rewrite the same links.
	return "update-account-ids"


def enqueue_account_id_update(company, user, enqueue):
	"""Queue the rename on the long worker. ``enqueue`` matches ``frappe.enqueue``."""
	job_id = account_id_job_id(company)
	enqueue(
		"logistics.logistics.account_ids.run_update_account_ids",
		queue="long",
		timeout=JOB_TIMEOUT,
		job_id=job_id,
		deduplicate=True,
		enqueue_after_commit=True,
		company=company or None,
		user=user,
	)
	return {"queued": True, "job_id": job_id}


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

	from frappe.utils.background_jobs import is_job_enqueued

	job_id = account_id_job_id(company)
	if is_job_enqueued(job_id):
		result["queued"] = True
		result["already_queued"] = True
		result["count"] = len(plan["updates"])
		return result

	enqueue_account_id_update(company, frappe.session.user, frappe.enqueue)
	result["queued"] = True
	result["count"] = len(plan["updates"])
	return result


def run_update_account_ids(company=None, user=None):
	"""Background job: rename Account IDs and tell the requesting user when it finishes."""
	import frappe
	from frappe import _

	if user:
		frappe.set_user(user)
	try:
		company = (company or "").strip()
		rows = _account_rows(company)
		abbrs = _company_abbreviations({row.company for row in rows if row.company})
		name_length = _account_id_length()
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
			name_length=name_length,
		)
		if plan["collisions"]:
			_notify_account_id_update(user, _collision_line(plan["collisions"][0]), indicator="red", company=company)
			return
		if not plan["updates"]:
			_notify_account_id_update(
				user,
				_("All Account IDs already match the current naming rule."),
				company=company,
			)
			return

		_ensure_gl_idle()
		total = len(plan["updates"]) * (2 if needs_temporary_ids(plan["updates"]) else 1)
		progress = {"done": 0}

		def rename(old, new):
			frappe.rename_doc(
				"Account",
				old,
				new,
				force=True,
				show_alert=False,
				rebuild_search=False,
			)

		def commit():
			frappe.db.commit()
			progress["done"] += 1
			try:
				frappe.publish_progress(
					progress["done"] / total * 100,
					title=_("Update Account IDs"),
					description=_("{0} of {1}").format(progress["done"], total),
				)
			except Exception:
				frappe.log_error(title="Update Account IDs progress", message=frappe.get_traceback())

		renamed = apply_account_id_updates(
			plan["updates"],
			rename,
			[row.name for row in rows],
			name_length=name_length,
			commit=commit,
		)
		frappe.enqueue(
			"frappe.utils.global_search.rebuild_for_doctype",
			queue="long",
			doctype="Account",
		)
		_notify_account_id_update(
			user,
			_("Updated {0} Account IDs").format(len(renamed)),
			company=company,
		)
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Update Account IDs", message=frappe.get_traceback())
		_notify_account_id_update(
			user,
			_("Updating Account IDs failed. See Error Log."),
			indicator="red",
			company=company,
		)
		raise


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


def _notify_account_id_update(user, message, indicator="green", company=None):
	import frappe

	if not user or not message:
		return
	payload = {"message": message, "indicator": indicator, "company": company or None}
	frappe.publish_realtime(event="logistics_account_ids_updated", message=payload, user=user)
	frappe.publish_realtime(
		event="msgprint",
		message={"message": message, "alert": 1, "indicator": indicator},
		user=user,
	)


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
