# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Transport vehicle permit eligibility, advance warnings, and dispatch blocking."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

STATUS_VALID = "Valid"
STATUS_EXPIRING = "Expiring Soon"
STATUS_EXPIRED = "Expired"

_DEFAULT_NOTIFY_ROLES = ("Transport Manager", "Land Transport Manager")


def enforcement_enabled() -> bool:
	return bool(cint(frappe.db.get_single_value("Transport Settings", "enforce_vehicle_permit_validation")))


def advance_warning_days() -> int:
	raw = frappe.db.get_single_value("Transport Settings", "permit_expiry_advance_warning")
	if raw is None or raw == "":
		return 1
	return max(0, cint(raw))


def classify_required_permit(valid_until, warning_days: int, as_of=None):
	"""Return (status, remaining_days) for a required permit, or None when it is still valid.

	Expired once today is on or after Valid Until. Expiring Soon while the date is still
	ahead and inside the advance-warning window. A blank date is neither.
	"""
	if not valid_until:
		return None
	as_of = getdate(as_of or today())
	expiry = getdate(valid_until)
	remaining = (expiry - as_of).days
	if remaining <= 0:
		return STATUS_EXPIRED, remaining
	if warning_days and remaining <= warning_days:
		return STATUS_EXPIRING, remaining
	return None


def format_expiry_date(value) -> str:
	expiry = getdate(value)
	return f"{expiry.strftime('%B')} {expiry.day}, {expiry.year}"


def expiring_soon_sentence(issue: dict) -> str:
	"""One-permit advance warning. One day remaining uses 'tomorrow'."""
	ident = issue.get("plate") or issue.get("vehicle_name") or issue.get("vehicle")
	permit = issue.get("permit_label") or issue.get("permit_type") or _("Permit")
	date_text = format_expiry_date(issue["valid_until"])
	days = cint(issue.get("remaining_days"))
	if days == 1:
		when = _("tomorrow ({0})").format(date_text)
	else:
		when = _("in {0} days ({1})").format(days, date_text)
	return _(
		"Vehicle {0}'s {1} will expire {2}. Please renew the permit to prevent the vehicle from becoming unavailable for dispatch."
	).format(ident, permit, when)


def expiring_soon_body(issues: list[dict]) -> str:
	if len(issues) == 1:
		return expiring_soon_sentence(issues[0])
	lines = []
	for issue in issues:
		name = issue.get("vehicle_name") or issue.get("vehicle")
		plate = issue.get("plate") or ""
		vehicle_bits = name if not plate or plate == name else f"{name} / {plate}"
		permit = issue.get("permit_label") or issue.get("permit_type") or _("Permit")
		days = cint(issue.get("remaining_days"))
		day_word = _("day") if days == 1 else _("days")
		lines.append(
			_("{0} — {1} — {2} — {3} {4} remaining").format(
				vehicle_bits,
				permit,
				format_expiry_date(issue["valid_until"]),
				days,
				day_word,
			)
		)
	return _(
		"The following permits are expiring soon. Renew them to prevent the vehicles from becoming unavailable for dispatch.\n{0}"
	).format("\n".join(lines))


def notification_subject(issue: dict) -> str:
	identity = _notification_identity(issue)
	permit = issue.get("permit_label") or issue.get("permit_type") or _("Permit")
	date_text = format_expiry_date(issue["valid_until"])
	if issue.get("status") == STATUS_EXPIRED:
		return _("Expired Permit: {0} — {1} expired on {2}. Status: Expired.").format(
			identity, permit, date_text
		)
	days = cint(issue.get("remaining_days"))
	if days == 1:
		when = _("expires tomorrow ({0})").format(date_text)
	else:
		when = _("expires in {0} days ({1})").format(days, date_text)
	return _("Permit Expiring Soon: {0} — {1} {2}. Status: Expiring Soon.").format(identity, permit, when)


def _notification_identity(issue: dict) -> str:
	name = issue.get("vehicle_name") or issue.get("vehicle")
	plate = issue.get("plate") or ""
	if plate and plate != name:
		return f"{name} / {plate}"
	return plate or name


def vehicle_dispatch_label(issue: dict) -> str:
	return _notification_identity(issue)


def assert_vehicle_dispatch_eligible(vehicle: str | None):
	"""Block dispatch when enforcement is on and a required permit has reached its date."""
	if not vehicle or not enforcement_enabled():
		return
	expired = [issue for issue in get_permit_issues(vehicle) if issue["status"] == STATUS_EXPIRED]
	if not expired:
		return
	details = " ".join(
		_("Permit {0} expired on {1}.").format(
			issue.get("permit_label") or issue.get("permit_type"),
			format_expiry_date(issue["valid_until"]),
		)
		for issue in expired
	)
	frappe.throw(
		_("Vehicle {0} is not eligible for dispatch. {1}").format(vehicle_dispatch_label(expired[0]), details),
		title=_("Not Eligible for Dispatch"),
	)


def expired_permit_reason(vehicle: str) -> str | None:
	"""Planner debug line. None when the vehicle may still be assigned."""
	if not vehicle or not enforcement_enabled():
		return None
	expired = [issue for issue in get_permit_issues(vehicle) if issue["status"] == STATUS_EXPIRED]
	if not expired:
		return None
	issue = expired[0]
	return (
		f"Vehicle {vehicle_dispatch_label(issue)} is not eligible for dispatch. "
		f"Permit {issue.get('permit_label') or issue.get('permit_type')} expired on "
		f"{format_expiry_date(issue['valid_until'])}."
	)


def get_permit_issues(vehicle: str) -> list[dict]:
	"""Expired and expiring required permits for one vehicle. Ignores the enforcement toggle."""
	if not vehicle or not _permits_ready():
		return []
	rows = frappe.db.sql(
		"""
		SELECT
			v.name AS vehicle,
			v.vehicle_name,
			v.license_plate_number AS plate,
			v.code,
			p.permit_type,
			p.valid_until,
			p.required
		FROM `tabTransport Vehicle` v
		INNER JOIN `tabTransport Vehicle Permits` p
			ON p.parent = v.name AND p.parenttype = 'Transport Vehicle'
		WHERE v.name = %(vehicle)s
		""",
		{"vehicle": vehicle},
		as_dict=True,
	)
	return _issues_from_rows(rows)


def get_vehicle_permit_status(vehicle: str) -> dict:
	issues = get_permit_issues(vehicle)
	expired = [issue for issue in issues if issue["status"] == STATUS_EXPIRED]
	if expired:
		return {"status": STATUS_EXPIRED, "issues": _public_issues(expired)}
	expiring = [issue for issue in issues if issue["status"] == STATUS_EXPIRING]
	if expiring:
		return {"status": STATUS_EXPIRING, "issues": _public_issues(expiring)}
	return {"status": STATUS_VALID, "issues": []}


@frappe.whitelist()
def get_vehicle_form_permit_status(vehicle: str):
	if not vehicle or not frappe.has_permission("Transport Vehicle", "read", vehicle):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return get_vehicle_permit_status(vehicle)


def get_open_permit_issues() -> list[dict]:
	"""Active vehicles with a required permit that is expired or inside the warning window."""
	if not _permits_ready():
		return []
	warning_days = advance_warning_days()
	horizon = add_days(getdate(today()), warning_days)
	rows = frappe.db.sql(
		"""
		SELECT
			v.name AS vehicle,
			v.vehicle_name,
			v.license_plate_number AS plate,
			v.code,
			p.permit_type,
			p.valid_until,
			p.required
		FROM `tabTransport Vehicle Permits` p
		INNER JOIN `tabTransport Vehicle` v ON v.name = p.parent
		WHERE p.parenttype = 'Transport Vehicle'
			AND IFNULL(v.is_active, 0) = 1
			AND IFNULL(p.required, 0) = 1
			AND p.valid_until IS NOT NULL
			AND p.valid_until <= %(horizon)s
		""",
		{"horizon": horizon},
		as_dict=True,
	)
	return _issues_from_rows(rows)


def expired_vehicle_names() -> set[str]:
	if not enforcement_enabled():
		return set()
	return {issue["vehicle"] for issue in get_open_permit_issues() if issue["status"] == STATUS_EXPIRED}


def banner_fingerprint(issues: list[dict]) -> str:
	parts = sorted(
		f"{issue['vehicle']}|{issue.get('permit_type')}|{getdate(issue['valid_until'])}|{issue['status']}"
		for issue in issues
	)
	return hashlib.sha1("\n".join(parts).encode()).hexdigest()


@frappe.whitelist()
def get_vehicle_permit_banners(kind: str | None = None, name: str | None = None):
	"""Desk banner payload. `applicable` is 0 when the route is outside Transport."""
	if kind and not route_is_transport(kind, name):
		return {"applicable": 0, "enabled": 0, "expiring": None, "expired": None}
	if not enforcement_enabled():
		return {"applicable": 1, "enabled": 0, "expiring": None, "expired": None}
	issues = get_open_permit_issues()
	expiring = [issue for issue in issues if issue["status"] == STATUS_EXPIRING]
	expired = [issue for issue in issues if issue["status"] == STATUS_EXPIRED]
	return {
		"applicable": 1,
		"enabled": 1,
		"expiring": _banner_block(expiring, "expiring") if expiring else None,
		"expired": _banner_block(expired, "expired") if expired else None,
	}


def route_is_transport(kind: str | None, name: str | None) -> bool:
	if not name:
		return False
	kind = (kind or "").strip().lower()
	label = name.strip()
	slug = label.lower().replace(" ", "-")
	if kind in ("workspace", "page_or_workspace", "page", "dashboard") and slug == "transport":
		return True
	if kind == "doctype":
		return frappe.db.get_value("DocType", label, "module") == "Transport"
	if kind == "report":
		return frappe.db.get_value("Report", label, "module") == "Transport"
	if kind == "dashboard":
		return frappe.db.get_value("Dashboard", label, "module") == "Transport" or slug == "transport"
	if kind in ("page", "page_or_workspace"):
		if slug in ("transport", "transport-operations", "run-sheet-scan"):
			return True
		for doctype, field in (("Page", "name"), ("Workspace", "name")):
			module = frappe.db.get_value(doctype, {field: label}, "module")
			if module == "Transport":
				return True
		page_module = frappe.db.get_value("Page", {"page_name": label}, "module")
		if page_module == "Transport":
			return True
		workspace_module = frappe.db.get_value("Workspace", {"label": label}, "module")
		return workspace_module == "Transport"
	return False


def _banner_block(issues: list[dict], kind: str) -> dict:
	if kind == "expired":
		return {
			"fingerprint": banner_fingerprint(issues),
			"title": _("Vehicle Permit Warning"),
			"body": _(
				"One or more transport vehicles have expired permits. "
				"These vehicles cannot be dispatched until their permits are renewed."
			),
		}
	return {
		"fingerprint": banner_fingerprint(issues),
		"title": _("Permit Expiring Soon"),
		"body": expiring_soon_body(issues),
	}


def notify_vehicle_permit_alerts():
	"""Daily desk notifications for expired and expiring required permits."""
	if not enforcement_enabled() or not _permits_ready():
		return
	users = notification_users()
	if not users:
		return
	for issue in get_open_permit_issues():
		if issue["status"] not in (STATUS_EXPIRED, STATUS_EXPIRING):
			continue
		subject = notification_subject(issue)
		_notify_once(users, issue["vehicle"], subject)


def notification_users() -> list[str]:
	role = frappe.db.get_single_value("Transport Settings", "permit_notify_role")
	roles = [role] if role else list(_DEFAULT_NOTIFY_ROLES)
	names = frappe.get_all(
		"Has Role",
		filters={"role": ["in", roles], "parenttype": "User"},
		pluck="parent",
		limit=500,
	)
	if not names:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", list(set(names))], "enabled": 1, "user_type": "System User"},
		pluck="name",
		limit=500,
	)


def _notify_once(users: list[str], vehicle: str, subject: str):
	if frappe.db.exists(
		"Notification Log",
		{"document_type": "Transport Vehicle", "document_name": vehicle, "subject": subject},
	):
		return
	for user in users:
		# Title is the in-app notification. Subject is mirrored for the email copy.
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"title": subject,
				"subject": subject,
				"for_user": user,
				"document_type": "Transport Vehicle",
				"document_name": vehicle,
				"from_user": frappe.session.user or "Administrator",
			}
		).insert(ignore_permissions=True)


def _permits_ready() -> bool:
	return frappe.db.table_exists("Transport Vehicle Permits") and frappe.db.has_column(
		"Transport Vehicle Permits", "required"
	)


def _issues_from_rows(rows: list[dict]) -> list[dict]:
	warning_days = advance_warning_days()
	as_of = getdate(today())
	labels = _permit_labels({row.get("permit_type") for row in rows if row.get("permit_type")})
	issues = []
	for row in rows:
		if not cint(row.get("required")) or not row.get("permit_type"):
			continue
		classified = classify_required_permit(row.get("valid_until"), warning_days, as_of)
		if not classified:
			continue
		status, remaining = classified
		issues.append(
			{
				"vehicle": row.get("vehicle"),
				"vehicle_name": row.get("vehicle_name") or row.get("code") or row.get("vehicle"),
				"plate": row.get("plate") or "",
				"permit_type": row.get("permit_type"),
				"permit_label": labels.get(row.get("permit_type")) or row.get("permit_type"),
				"valid_until": getdate(row.get("valid_until")),
				"status": status,
				"remaining_days": remaining,
			}
		)
	issues.sort(key=lambda issue: (issue["valid_until"], issue["vehicle"], issue["permit_type"]))
	return issues


def _permit_labels(permit_types: set[str]) -> dict[str, str]:
	if not permit_types:
		return {}
	rows = frappe.get_all(
		"License and Permit Type",
		filters={"name": ["in", list(permit_types)]},
		fields=["name", "description"],
		limit=len(permit_types),
	)
	return {row.name: (row.description or row.name) for row in rows}


def _public_issues(issues: list[dict]) -> list[dict]:
	public = []
	for issue in issues:
		public.append(
			{
				"vehicle": issue["vehicle"],
				"vehicle_name": issue["vehicle_name"],
				"plate": issue["plate"],
				"permit_type": issue["permit_type"],
				"permit_label": issue["permit_label"],
				"valid_until": str(issue["valid_until"]),
				"status": issue["status"],
				"remaining_days": issue["remaining_days"],
			}
		)
	return public


def _parse_filters(filters: Any) -> dict:
	if not filters:
		return {}
	if isinstance(filters, str):
		try:
			parsed = json.loads(filters)
		except Exception:
			return {}
		return parsed if isinstance(parsed, dict) else {}
	if isinstance(filters, dict):
		return dict(filters)
	return {}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def transport_vehicle_query(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, reference_doctype=None, ignore_user_permissions=False
):
	"""Active Transport Vehicles. Expired required permits are omitted while enforcement is on."""
	_ = (doctype, searchfield, as_dict, reference_doctype, ignore_user_permissions)
	f = _parse_filters(filters)
	start = cint(start)
	page_len = cint(page_len) or 20
	conditions = ["IFNULL(is_active, 0) = 1"]
	params: dict[str, Any] = {"start": start, "page_len": page_len}
	vehicle_type = f.get("vehicle_type")
	if vehicle_type:
		conditions.append("vehicle_type = %(vehicle_type)s")
		params["vehicle_type"] = vehicle_type
	else:
		conditions.append("(vehicle_type IS NULL OR vehicle_type = '')")
	if txt:
		conditions.append(
			"(name LIKE %(txt)s OR vehicle_name LIKE %(txt)s OR IFNULL(license_plate_number, '') LIKE %(txt)s)"
		)
		params["txt"] = f"%{txt}%"
	expired = expired_vehicle_names()
	if expired:
		conditions.append("name NOT IN %(expired)s")
		params["expired"] = tuple(expired)
	sql = f"""
		SELECT name, vehicle_name, license_plate_number
		FROM `tabTransport Vehicle`
		WHERE {" AND ".join(conditions)}
		ORDER BY modified DESC
		LIMIT %(start)s, %(page_len)s
	"""
	return frappe.db.sql(sql, params)
