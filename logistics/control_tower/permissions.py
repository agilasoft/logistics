# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Permission query conditions for Control Tower doctypes.

Restricts row visibility based on the ``Control Tower Organization`` access list
attached to the User document. Falls open (no restriction) for:
- Administrator
- Users carrying ``System Manager`` or ``Control Tower Manager`` roles
- Users whose User profile does not yet have any ``ct_organizations`` mapping
  configured (so the feature is opt-in per tenant).

To enable per-org row filtering for a user:
- Edit their ``User`` record
- Open the ``Control Tower Access`` child table (custom field, optional)
- Add one row per organization the user is allowed to see.

If the tenant hasn't added that custom field, the helpers fall open. This way
the install is non-disruptive.
"""

from __future__ import unicode_literals

import frappe


CT_DOCTYPES_BY_ORG_FIELD = {
	"Control Tower GP Target": "organization",
	"Pipeline Entry": "organization",
	"Risk Register Entry": "organization",
}


def _allowed_orgs(user=None):
	"""Return the list of organizations the user is allowed to see.

	Empty list means "no restriction" (fall open). A non-empty list narrows
	queries to entries whose ``organization`` is in the list.
	"""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return []
	roles = set(frappe.get_roles(user))
	if "System Manager" in roles or "Control Tower Manager" in roles:
		return []
	# Lookup the user-level access list. If the custom field is not present in
	# this tenant we fall open.
	if not frappe.db.exists("DocType", "User"):
		return []
	try:
		rows = frappe.get_all(
			"Control Tower User Org Access",
			filters={"parenttype": "User", "parent": user},
			fields=["organization"],
		)
	except Exception:
		return []
	return [r["organization"] for r in rows if r.get("organization")]


def _build_condition(allowed, table_alias):
	"""Build the SQL fragment that filters ``organization`` to ``allowed``."""
	if not allowed:
		return ""
	placeholders = ",".join(["{0}".format(frappe.db.escape(v)) for v in allowed])
	return "`{alias}`.`organization` in ({values})".format(alias=table_alias, values=placeholders)


def gp_target(user=None):
	allowed = _allowed_orgs(user)
	if not allowed:
		return ""
	return _build_condition(allowed, "tabControl Tower GP Target")


def pipeline_entry(user=None):
	allowed = _allowed_orgs(user)
	if not allowed:
		return ""
	return _build_condition(allowed, "tabPipeline Entry")


def risk_register_entry(user=None):
	allowed = _allowed_orgs(user)
	if not allowed:
		return ""
	return _build_condition(allowed, "tabRisk Register Entry")


def returned_billing(user=None):
	"""Returned Billing has no organization field; instead, gate by the user
	being allowed to see at least one organization (i.e. they're a CT viewer).
	"""
	user = user or frappe.session.user
	if not user or user == "Administrator":
		return ""
	roles = set(frappe.get_roles(user))
	if {"System Manager", "Control Tower Manager", "Control Tower Viewer", "Accounts User", "Accounts Manager"} & roles:
		return ""
	return "1=0"


def organization(user=None):
	"""Control Tower Organization registry: managers see all; viewers see only
	the orgs in their allowed list (or all if no list configured).
	"""
	allowed = _allowed_orgs(user)
	if not allowed:
		return ""
	placeholders = ",".join(["{0}".format(frappe.db.escape(v)) for v in allowed])
	return "`tabControl Tower Organization`.`name` in ({0})".format(placeholders)
