# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Session defaults collected before a desk user opens a workdesk."""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _

# Forms and reports call get_user_default("Company"). That server lookup ignores
# a plain string stored under "Company" and reads the scrubbed key "company".
# MariaDB's collation also treats those two keys as one row, so the value has
# to be stored as "company". Reading still accepts either spelling.
COMPANY_DEFAULT_KEY = "company"
# Logout clears every Company default listed in Session Default Settings.
# These extra keys are not in that list, so the user's choices survive logout.
PERSISTENT_COMPANY_KEY = "logistics_session_company"

# Branch is company-scoped through custom_company when that field exists.
# Cost Center and Profit Center are company-scoped through company.
DIMENSIONS = (
	{
		"doctype": "Branch",
		"fieldname": "branch",
		"label": "Branch",
		"filters": {},
	},
	{
		"doctype": "Cost Center",
		"fieldname": "cost_center",
		"label": "Cost Center",
		"filters": {"is_group": 0, "disabled": 0},
	},
	{
		"doctype": "Profit Center",
		"fieldname": "profit_center",
		"label": "Profit Center",
		"filters": {},
	},
)


def extend_bootinfo(bootinfo) -> None:
	"""Tell the desk whether this user still has to choose session defaults."""
	if bootinfo is None or getattr(frappe.flags, "in_install", False):
		return
	try:
		saved = restore_persistent_defaults()
		user = getattr(bootinfo, "user", None)
		defaults = getattr(user, "defaults", None) if user is not None else None
		if isinstance(defaults, dict):
			for key, value in saved.items():
				if not value:
					continue
				defaults[key] = value
				defaults[frappe.unscrub(key)] = value
	except Exception:
		pass
	try:
		bootinfo.logistics_needs_session_defaults = 1 if user_needs_session_defaults() else 0
	except Exception:
		bootinfo.logistics_needs_session_defaults = 0
	try:
		_point_session_defaults_menu(bootinfo)
	except Exception:
		return


def user_needs_session_defaults(user: str | None = None) -> bool:
	"""True when a desk user must finish session defaults before a workdesk."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	# The desk itself will not leave the setup wizard until the site is set up.
	# Redirecting away from that wizard loops the two routes.
	if not frappe.is_setup_complete():
		return False
	if frappe.db.get_value("User", user, "user_type") != "System User":
		return False
	company = get_personal_company(user)
	if not company:
		return bool(get_permitted_companies(user))
	return _missing_dimension(user, company)


def get_personal_company(user: str | None = None) -> str | None:
	"""Return the Company this user saved, ignoring Global Defaults."""
	user = user or frappe.session.user
	return _personal_value(user, COMPANY_DEFAULT_KEY, PERSISTENT_COMPANY_KEY)


def get_permitted_companies(user: str | None = None) -> list[str]:
	"""Companies the user is allowed to read."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []
	if not frappe.db.exists("DocType", "Company"):
		return []
	try:
		with _as_user(user):
			return frappe.get_list(
				"Company",
				pluck="name",
				order_by="name asc",
				limit=0,
			)
	except frappe.PermissionError:
		return []


@frappe.whitelist()
def get_context():
	"""Permitted companies, dimensions, and the user's current personal defaults."""
	_require_system_user()
	user = frappe.session.user
	company = get_personal_company(user)
	companies = get_permitted_companies(user)
	rows = {spec["fieldname"]: _dimension_rows(spec, user) for spec in DIMENSIONS}
	selected = company if company in companies else None
	values = _values_for_company(user, selected, rows) if selected else {}
	payload = {
		"companies": companies,
		"company": selected,
		"required": user_needs_session_defaults(user),
		"branches": rows["branch"],
		"cost_centers": rows["cost_center"],
		"profit_centers": rows["profit_center"],
	}
	payload.update(values)
	return payload


@frappe.whitelist()
def save_session_defaults(
	company: str | None = None,
	branch: str | None = None,
	cost_center: str | None = None,
	profit_center: str | None = None,
):
	"""Store the user's personal Company, Branch, Cost Center, and Profit Center."""
	_require_system_user()
	user = frappe.session.user
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Company is required"))

	permitted = set(get_permitted_companies(user))
	if company not in permitted:
		frappe.throw(_("You cannot use Company {0}").format(company), frappe.PermissionError)

	incoming = {
		"branch": branch,
		"cost_center": cost_center,
		"profit_center": profit_center,
	}
	saved = {"company": company}
	for spec in DIMENSIONS:
		fieldname = spec["fieldname"]
		value = (incoming.get(fieldname) or "").strip()
		allowed = _names_for_company(_dimension_rows(spec, user), company)
		if allowed and not value:
			frappe.throw(_("{0} is required").format(_(spec["label"])))
		if value and value not in allowed:
			frappe.throw(
				_("You cannot use {0} {1}").format(_(spec["label"]), value),
				frappe.PermissionError,
			)
		_store_default(user, fieldname, f"logistics_session_{fieldname}", value)
		saved[fieldname] = value or None

	_store_default(user, COMPANY_DEFAULT_KEY, PERSISTENT_COMPANY_KEY, company)
	return saved


def restore_persistent_company(user: str | None = None) -> str | None:
	"""Put the saved company back after logout clears the session default."""
	return restore_persistent_defaults(user).get("company")


def restore_persistent_defaults(user: str | None = None) -> dict:
	"""Put saved session defaults back after logout clears the session keys."""
	user = user or frappe.session.user
	restored = {}
	if not user or user == "Guest":
		return restored
	restored["company"] = _restore_one(user, COMPANY_DEFAULT_KEY, PERSISTENT_COMPANY_KEY)
	for spec in DIMENSIONS:
		fieldname = spec["fieldname"]
		restored[fieldname] = _restore_one(user, fieldname, f"logistics_session_{fieldname}")
	return restored


def _missing_dimension(user: str, company: str) -> bool:
	for spec in DIMENSIONS:
		names = _names_for_company(_dimension_rows(spec, user), company)
		if names and not _valid_personal(user, spec["fieldname"], company, names):
			return True
	return False


def _values_for_company(user: str, company: str, rows: dict) -> dict:
	values = {}
	for spec in DIMENSIONS:
		fieldname = spec["fieldname"]
		names = _names_for_company(rows[fieldname], company)
		values[fieldname] = _valid_personal(user, fieldname, company, names)
	return values


def _valid_personal(user: str, fieldname: str, company: str, names: list[str]) -> str | None:
	value = _personal_value(user, fieldname, f"logistics_session_{fieldname}")
	if value and value in names:
		return value
	return None


def _personal_value(user: str, fieldname: str, persistent_key: str) -> str | None:
	defaults = frappe.defaults.get_defaults_for(user) or {}
	for key in (fieldname, frappe.unscrub(fieldname), persistent_key):
		value = defaults.get(key)
		if isinstance(value, (list, tuple)):
			value = value[0] if value else None
		if value:
			return value
	return None


def _dimension_rows(spec: dict, user: str) -> list[dict]:
	doctype = spec["doctype"]
	if not user or user == "Guest" or not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	company_field = _company_field(meta)
	filters = {key: value for key, value in spec.get("filters", {}).items() if meta.has_field(key)}
	fields = ["name"]
	if company_field:
		fields.append(company_field)
	try:
		with _as_user(user):
			rows = frappe.get_list(
				doctype,
				fields=fields,
				filters=filters,
				order_by="name asc",
				limit=0,
			)
	except frappe.PermissionError:
		return []
	return [
		{
			"name": row.name,
			"company": (row.get(company_field) if company_field else "") or "",
		}
		for row in rows
	]


def _names_for_company(rows: list[dict], company: str) -> list[str]:
	return [row["name"] for row in rows if not row.get("company") or row.get("company") == company]


def _company_field(meta) -> str | None:
	for fieldname in ("custom_company", "company"):
		if meta.has_field(fieldname):
			return fieldname
	return None


def _store_default(user: str, fieldname: str, persistent_key: str, value: str | None) -> None:
	# Drop a title-case row first. If it already holds this value, set_default
	# would keep the old key and get_user_default would stay empty.
	frappe.defaults.clear_user_default(frappe.unscrub(fieldname), user)
	frappe.defaults.clear_user_default(fieldname, user)
	frappe.defaults.clear_user_default(persistent_key, user)
	if not value:
		return
	frappe.defaults.set_user_default(fieldname, value, user=user)
	frappe.defaults.set_user_default(persistent_key, value, user=user)


def _restore_one(user: str, fieldname: str, persistent_key: str) -> str | None:
	defaults = frappe.defaults.get_defaults_for(user) or {}
	saved = defaults.get(persistent_key)
	if isinstance(saved, (list, tuple)):
		saved = saved[0] if saved else None
	if not saved:
		return None
	current = defaults.get(fieldname) or defaults.get(frappe.unscrub(fieldname))
	if isinstance(current, (list, tuple)):
		current = current[0] if current else None
	if current != saved:
		frappe.defaults.clear_user_default(frappe.unscrub(fieldname), user)
		frappe.defaults.set_user_default(fieldname, saved, user=user)
	return saved


def _require_system_user() -> None:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Login required"), frappe.PermissionError)
	if frappe.db.get_value("User", user, "user_type") != "System User":
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _point_session_defaults_menu(bootinfo) -> None:
	"""Open this page from the user menu instead of the framework dialog."""
	navbar = bootinfo.get("navbar_settings") if hasattr(bootinfo, "get") else None
	if not navbar or not hasattr(navbar, "get"):
		return
	dropdown = navbar.get("settings_dropdown")
	if not dropdown:
		return

	for item in dropdown:
		if not hasattr(item, "get") or item.get("item_label") != "Session Defaults":
			continue
		item.item_type = "Route"
		item.route = "/desk/session-defaults"
		item.action = ""
		item.hidden = 0
		return

	dropdown.append(
		frappe._dict(
			item_label="Session Defaults",
			item_type="Route",
			route="/desk/session-defaults",
			action="",
			hidden=0,
			is_standard=1,
		)
	)


@contextmanager
def _as_user(user: str):
	previous = frappe.session.user
	switched = previous != user
	if switched:
		frappe.set_user(user)
	try:
		yield
	finally:
		if switched:
			frappe.set_user(previous)
