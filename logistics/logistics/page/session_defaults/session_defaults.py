# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Session defaults collected before a desk user opens a workdesk.

Which fields appear comes from Session Default Settings. Company, Branch,
Cost Center, and Profit Center are not added unless that list includes them.
"""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _

# Forms and reports call get_user_default("Company"). That server lookup ignores
# a plain string stored under "Company" and reads the scrubbed key "company".
# MariaDB's collation also treats those two keys as one row, so the value has
# to be stored as "company". Reading still accepts either spelling.
COMPANY_DEFAULT_KEY = "company"
# Logout clears every default listed in Session Default Settings.
# The matching logistics_session_* key is not one of those, so the choice can be put back.
PERSISTENT_COMPANY_KEY = "logistics_session_company"

# How a DocType on Session Default Settings is filtered, and whether the page
# requires it. Any other listed DocType is an optional link with no extra filters.
_FIELD_BEHAVIOR = {
	"Company": {
		"fieldname": "company",
		"label": "Company",
		"required": True,
		"persistent_key": PERSISTENT_COMPANY_KEY,
	},
	"Branch": {
		"fieldname": "branch",
		"label": "Branch",
		"required": True,
		"filters": {},
	},
	"Cost Center": {
		"fieldname": "cost_center",
		"label": "Cost Center",
		"filters": {"is_group": 0, "disabled": 0},
	},
	"Profit Center": {
		"fieldname": "profit_center",
		"label": "Profit Center",
		"filters": {"is_active": 1},
	},
}


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
	specs = configured_specs()
	company_spec = _spec_by_fieldname(specs, "company")
	if not company_spec:
		return False
	company = get_personal_company(user)
	if not company:
		return bool(get_permitted_companies(user))
	return _missing_required_dimension(user, company, specs)


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


def configured_specs() -> list[dict]:
	"""Field specs for the DocTypes listed on Session Default Settings, in list order."""
	specs = []
	seen = set()
	for ref_doctype in _configured_ref_doctypes():
		if ref_doctype in seen:
			continue
		seen.add(ref_doctype)
		specs.append(_spec_for(ref_doctype))
	return specs


@frappe.whitelist()
def get_context():
	"""Permitted values and the user's current defaults, for the configured fields only."""
	_require_system_user()
	user = frappe.session.user
	specs = configured_specs()
	company_spec = _spec_by_fieldname(specs, "company")
	dimension_specs = [spec for spec in specs if spec["doctype"] != "Company"]
	rows = {spec["fieldname"]: _dimension_rows(spec, user) for spec in dimension_specs}
	companies = get_permitted_companies(user)
	company = get_personal_company(user) if company_spec else None
	selected = company if company in companies else None
	scope_company = selected if company_spec else (get_personal_company(user) or "")
	if not company_spec and scope_company:
		rows = {
			fieldname: [
				row
				for row in field_rows
				if not row.get("company") or row.get("company") == scope_company
			]
			for fieldname, field_rows in rows.items()
		}
	if scope_company:
		values = _values_for_company(user, scope_company, rows, dimension_specs)
	else:
		values = {spec["fieldname"]: None for spec in dimension_specs}
	payload = {
		"fields": [_public_field(spec) for spec in specs],
		"companies": companies,
		"company": selected,
		"required": user_needs_session_defaults(user),
		"branches": rows.get("branch", []),
		"cost_centers": rows.get("cost_center", []),
		"profit_centers": rows.get("profit_center", []),
		"options": {spec["fieldname"]: rows[spec["fieldname"]] for spec in dimension_specs},
	}
	if company_spec:
		payload["options"]["company"] = companies
	payload.update(values)
	return payload


@frappe.whitelist()
def save_session_defaults(
	company: str | None = None,
	branch: str | None = None,
	cost_center: str | None = None,
	profit_center: str | None = None,
	values: str | dict | None = None,
):
	"""Store the user's defaults for the DocTypes listed in Session Default Settings."""
	_require_system_user()
	user = frappe.session.user
	specs = configured_specs()
	incoming = _incoming_values(company, branch, cost_center, profit_center, values)
	company_spec = _spec_by_fieldname(specs, "company")
	saved = {}
	applied = {}
	cleared = []

	scope_company = ""
	if company_spec:
		scope_company = (incoming.get("company") or "").strip()
		if not scope_company:
			frappe.throw(_("Company is required"))
		permitted = set(get_permitted_companies(user))
		if scope_company not in permitted:
			frappe.throw(
				_("You cannot use Company {0}").format(scope_company),
				frappe.PermissionError,
			)
		_store_default(user, COMPANY_DEFAULT_KEY, company_spec["persistent_key"], scope_company)
		saved["company"] = scope_company
		applied.update(_applied_keys(COMPANY_DEFAULT_KEY, scope_company))
	else:
		scope_company = get_personal_company(user) or ""

	for spec in specs:
		if spec["doctype"] == "Company":
			continue
		fieldname = spec["fieldname"]
		value = (incoming.get(fieldname) or "").strip()
		allowed = _names_for_company(_dimension_rows(spec, user), scope_company)
		if spec.get("required") and allowed and not value:
			frappe.throw(_("{0} is required").format(_(spec["label"])))
		if value and value not in allowed:
			frappe.throw(
				_("You cannot use {0} {1}").format(_(spec["label"]), value),
				frappe.PermissionError,
			)
		_store_default(user, fieldname, spec["persistent_key"], value or None)
		saved[fieldname] = value or None
		if value:
			applied.update(_applied_keys(fieldname, value))
		else:
			_remember_cleared(cleared, fieldname, spec["persistent_key"])

	_clear_unconfigured(user, specs, cleared)
	saved["applied"] = applied
	saved["cleared"] = cleared
	return saved


def restore_persistent_company(user: str | None = None) -> str | None:
	"""Put the saved company back after logout clears the session default."""
	return restore_persistent_defaults(user).get("company")


def restore_persistent_defaults(user: str | None = None) -> dict:
	"""Put saved session defaults back after logout clears the keys listed in settings."""
	user = user or frappe.session.user
	restored = {}
	if not user or user == "Guest":
		return restored
	specs = configured_specs()
	# A DocType removed from Session Default Settings should stop applying on the next login.
	_clear_unconfigured(user, specs, [])
	for spec in specs:
		restored[spec["fieldname"]] = _restore_one(user, spec["fieldname"], spec["persistent_key"])
	return restored


def _configured_ref_doctypes() -> list[str]:
	if not frappe.db.exists("DocType", "Session Default"):
		return []
	rows = frappe.get_all(
		"Session Default",
		filters={
			"parent": "Session Default Settings",
			"parenttype": "Session Default Settings",
		},
		fields=["ref_doctype"],
		order_by="idx asc",
		ignore_permissions=True,
	)
	names = []
	for row in rows:
		ref_doctype = (row.ref_doctype or "").strip()
		if ref_doctype:
			names.append(ref_doctype)
	return names


def _spec_for(ref_doctype: str) -> dict:
	behavior = _FIELD_BEHAVIOR.get(ref_doctype) or {}
	fieldname = behavior.get("fieldname") or frappe.scrub(ref_doctype)
	return {
		"doctype": ref_doctype,
		"fieldname": fieldname,
		"label": behavior.get("label") or ref_doctype,
		"filters": behavior.get("filters") or {},
		"required": bool(behavior.get("required")),
		"persistent_key": behavior.get("persistent_key") or f"logistics_session_{fieldname}",
	}


def _spec_by_fieldname(specs: list[dict], fieldname: str) -> dict | None:
	for spec in specs:
		if spec["fieldname"] == fieldname:
			return spec
	return None


def _public_field(spec: dict) -> dict:
	return {
		"fieldname": spec["fieldname"],
		"doctype": spec["doctype"],
		"label": _(spec["label"]),
		"required": 1 if spec.get("required") else 0,
	}


def _incoming_values(
	company: str | None,
	branch: str | None,
	cost_center: str | None,
	profit_center: str | None,
	values: str | dict | None,
) -> dict:
	incoming = {}
	if isinstance(values, str) and values:
		values = frappe.parse_json(values)
	if isinstance(values, dict):
		incoming.update(values)
	for fieldname, value in (
		("company", company),
		("branch", branch),
		("cost_center", cost_center),
		("profit_center", profit_center),
	):
		if value is not None:
			incoming[fieldname] = value
	return incoming


def _applied_keys(fieldname: str, value: str) -> dict:
	return {fieldname: value, frappe.unscrub(fieldname): value}


def _remember_cleared(cleared: list[str], fieldname: str, persistent_key: str) -> None:
	for key in (fieldname, frappe.unscrub(fieldname), persistent_key):
		if key not in cleared:
			cleared.append(key)


def _clear_unconfigured(user: str, specs: list[dict], cleared: list[str]) -> None:
	"""Drop defaults this page stored for DocTypes no longer listed in settings."""
	keep = {spec["persistent_key"] for spec in specs}
	defaults = frappe.defaults.get_defaults_for(user) or {}
	for key in list(defaults):
		text = str(key)
		if not text.startswith("logistics_session_") or text in keep:
			continue
		fieldname = text[len("logistics_session_") :]
		_store_default(user, fieldname, text, None)
		_remember_cleared(cleared, fieldname, text)


def _missing_required_dimension(user: str, company: str, specs: list[dict]) -> bool:
	"""True when a required field other than Company, such as Branch, is still unset."""
	for spec in specs:
		if spec["doctype"] == "Company" or not spec.get("required"):
			continue
		names = _names_for_company(_dimension_rows(spec, user), company)
		if names and not _valid_personal(user, spec["fieldname"], names):
			return True
	return False


def _values_for_company(user: str, company: str, rows: dict, specs: list[dict]) -> dict:
	values = {}
	for spec in specs:
		fieldname = spec["fieldname"]
		names = _names_for_company(rows.get(fieldname) or [], company)
		values[fieldname] = _valid_personal(user, fieldname, names)
	return values


def _valid_personal(user: str, fieldname: str, names: list[str]) -> str | None:
	persistent_key = (
		PERSISTENT_COMPANY_KEY if fieldname == COMPANY_DEFAULT_KEY else f"logistics_session_{fieldname}"
	)
	value = _personal_value(user, fieldname, persistent_key)
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
