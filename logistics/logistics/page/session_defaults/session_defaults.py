# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Company session default collected before a desk user opens a workdesk."""

from __future__ import annotations

import frappe
from frappe import _

# Forms and reports call get_user_default("Company"). That server lookup ignores
# a plain string stored under "Company" and reads the scrubbed key "company".
# MariaDB's collation also treats those two keys as one row, so the value has
# to be stored as "company". Reading still accepts either spelling.
COMPANY_DEFAULT_KEYS = ("Company", "company")
COMPANY_DEFAULT_KEY = "company"


def extend_bootinfo(bootinfo) -> None:
	"""Tell the desk whether this user still has to choose a Company."""
	if bootinfo is None or getattr(frappe.flags, "in_install", False):
		return
	try:
		bootinfo.logistics_needs_session_defaults = 1 if user_needs_session_defaults() else 0
	except Exception:
		bootinfo.logistics_needs_session_defaults = 0
	try:
		_point_session_defaults_menu(bootinfo)
	except Exception:
		return


def user_needs_session_defaults(user: str | None = None) -> bool:
	"""True when a desk user must choose a Company before using a workdesk."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if frappe.db.get_value("User", user, "user_type") != "System User":
		return False
	if get_personal_company(user):
		return False
	return bool(get_permitted_companies(user))


def get_personal_company(user: str | None = None) -> str | None:
	"""Return the Company this user saved, ignoring Global Defaults."""
	user = user or frappe.session.user
	defaults = frappe.defaults.get_defaults_for(user) or {}
	for key in COMPANY_DEFAULT_KEYS:
		value = defaults.get(key)
		if isinstance(value, (list, tuple)):
			value = value[0] if value else None
		if value:
			return value
	return None


def get_permitted_companies(user: str | None = None) -> list[str]:
	"""Companies the user is allowed to read."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []
	if not frappe.db.exists("DocType", "Company"):
		return []

	previous = frappe.session.user
	switched = previous != user
	if switched:
		frappe.set_user(user)
	try:
		return frappe.get_list(
			"Company",
			pluck="name",
			order_by="name asc",
			limit_page_length=0,
		)
	finally:
		if switched:
			frappe.set_user(previous)


@frappe.whitelist()
def get_context():
	"""Permitted companies and the user's current personal Company default."""
	_require_system_user()
	company = get_personal_company()
	companies = get_permitted_companies()
	return {
		"companies": companies,
		"company": company,
		"required": user_needs_session_defaults(),
	}


@frappe.whitelist()
def save_session_defaults(company: str | None = None):
	"""Store the user's personal Company default."""
	_require_system_user()
	company = (company or "").strip()
	if not company:
		frappe.throw(_("Company is required"))

	permitted = set(get_permitted_companies())
	if company not in permitted:
		frappe.throw(_("You cannot use Company {0}").format(company), frappe.PermissionError)

	user = frappe.session.user
	# Drop a title-case row first. If it already holds this company, set_default
	# would keep the old key and get_user_default("Company") would stay empty.
	frappe.defaults.clear_user_default("Company", user)
	frappe.defaults.set_user_default(COMPANY_DEFAULT_KEY, company, user=user)
	return {"company": company}


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
