# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Gate internal job / operational-leg creation: requires charges AND a matching Internal Job setup."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.internal_job_persistence import internal_job_detail_fieldname
from logistics.utils.linked_service_compat import linked_service_rows
from logistics.utils.sales_quote_charge_parameters import (
	any_programme_charge_matches_params_dict,
	any_sales_quote_charge_matches_internal_job_detail_params,
	coerce_sales_quote_name,
	extract_service_scoped_quote_parameters,
	sales_quote_charge_row_matches_internal_job_detail_params,
)
from logistics.utils.sales_quote_service_eligibility import sales_quote_has_service_charges

_PROGRAMME_CHARGE_PARENTS = frozenset(
	{
		"Special Project",
		"MICE Project",
		"Exhibit",
		"MICE Job",
		"MICE Order",
		"Docket",
		"Project Job",
	}
)

# Programme parents that store planned legs on ``lifecycle_jobs`` (eligibility only — not
# ``INTERNAL_JOB_DETAIL_PARENTS``, which would auto-create Internal Job documents on save).
_PROGRAMME_LIFECYCLE_JOB_PARENTS: dict[str, str] = {
	"Special Project": "special_project_services",
	"Exhibit": "lifecycle_jobs",
}

_EXHIBIT_LINKED_SALES_QUOTE_PARENTS = frozenset({"MICE Project", "Exhibit"})


def _lookup_submitted_sales_quote_for_exhibit(exhibit_name: str) -> str:
	exhibit_name = (exhibit_name or "").strip()
	if not exhibit_name:
		return ""
	return (
		frappe.db.get_value(
			"Sales Quote",
			{"exhibit": exhibit_name, "docstatus": 1},
			"name",
			order_by="modified desc",
		)
		or ""
	)


def _row_val(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _resolve_sales_quote_name(sales_quote: str | Any | None, parent_doc: Any | None) -> str:
	sq = coerce_sales_quote_name(sales_quote)
	if sq:
		return sq
	if parent_doc is not None:
		sq = coerce_sales_quote_name(getattr(parent_doc, "sales_quote", None))
		if sq:
			return sq
		dt = getattr(parent_doc, "doctype", None) or ""
		name = (getattr(parent_doc, "name", None) or "").strip()
		if dt in _EXHIBIT_LINKED_SALES_QUOTE_PARENTS and name:
			linked = _lookup_submitted_sales_quote_for_exhibit(name)
			if linked:
				return linked
		if dt == "Docket":
			linked = _lookup_submitted_sales_quote_for_exhibit(
				(getattr(parent_doc, "exhibit", None) or "").strip()
			)
			if linked:
				return linked
	return ""


def _programme_charges_for_service(parent_doc: Any, service_type_label: str) -> list[Any]:
	if not parent_doc or getattr(parent_doc, "doctype", None) not in _PROGRAMME_CHARGE_PARENTS:
		return []
	from logistics.special_projects.special_project_charge_lifecycle import (
		programme_charges_for_service_type,
	)

	return programme_charges_for_service_type(parent_doc, service_type_label)


def charges_exist_for_service(
	sales_quote: str | None,
	parent_doc: Any | None,
	service_type_label: str,
) -> bool:
	"""True when the linked quote or programme parent has at least one charge for *service_type_label*."""
	st = (service_type_label or "").strip()
	if not st:
		return False

	sq_name = _resolve_sales_quote_name(sales_quote, parent_doc)
	if sq_name and frappe.db.exists("Sales Quote", sq_name):
		if sales_quote_has_service_charges(sq_name, st):
			return True
		if sales_quote_charge_service_types_equal(st, "Customs") and sales_quote_has_service_charges(
			sq_name, "Custom"
		):
			return True

	if _programme_charges_for_service(parent_doc, st):
		return True

	return False


def internal_job_matches_charges(
	sales_quote: str | None,
	parent_doc: Any | None,
	ij_row: Any,
	service_type_label: str,
) -> bool:
	"""True when *ij_row* parameters match at least one charge row for the service."""
	if not ij_row:
		return False

	st = (service_type_label or "").strip()
	if not st:
		return False

	ij_params = extract_service_scoped_quote_parameters(ij_row, st)
	sq_name = _resolve_sales_quote_name(sales_quote, parent_doc)

	if sq_name and frappe.db.exists("Sales Quote", sq_name):
		if any_sales_quote_charge_matches_internal_job_detail_params(sq_name, ij_row, st):
			return True

	programme_rows = _programme_charges_for_service(parent_doc, st)
	if programme_rows:
		if not ij_params:
			return True
		return any_programme_charge_matches_params_dict(parent_doc, ij_params, st)

	return False


def _ij_rows_same_identity(a: Any, b: Any) -> bool:
	if a is b:
		return True
	a_ij = (_row_val(a, "internal_job") or "").strip()
	b_ij = (_row_val(b, "internal_job") or "").strip()
	if a_ij and b_ij and a_ij == b_ij:
		return True
	a_name = (_row_val(a, "name") or "").strip()
	b_name = (_row_val(b, "name") or "").strip()
	if a_name and b_name and a_name == b_name:
		return True
	return False


def _quote_ij_rows_match_candidate(quote_row: Any, ij_row: Any, service_type_label: str) -> bool:
	if not sales_quote_charge_service_types_equal(
		_row_val(quote_row, "service_type"), service_type_label
	):
		return False
	if _ij_rows_same_identity(quote_row, ij_row):
		return True
	quote_params = extract_service_scoped_quote_parameters(quote_row, service_type_label)
	ij_params = extract_service_scoped_quote_parameters(ij_row, service_type_label)
	if not quote_params and not ij_params:
		return True
	if not quote_params or not ij_params:
		return False
	return quote_params == ij_params


def _parent_ij_fieldname(parent_doctype: str) -> str | None:
	"""Child table field for internal-job / lifecycle planning rows on *parent_doctype*."""
	dt = (parent_doctype or "").strip()
	if not dt:
		return None
	# Programme parents migrated planned legs to lifecycle_jobs; do not fall back to
	# internal_job_details (Special Project) or internal_jobs (Exhibit) for eligibility.
	if dt in _PROGRAMME_LIFECYCLE_JOB_PARENTS:
		return _PROGRAMME_LIFECYCLE_JOB_PARENTS[dt]
	return internal_job_detail_fieldname(dt)


def _parent_uses_lifecycle_jobs(parent_doc: Any | None) -> bool:
	dt = getattr(parent_doc, "doctype", None) or ""
	return dt in _PROGRAMME_LIFECYCLE_JOB_PARENTS


def _parent_has_ij_row(parent_doc: Any, ij_row: Any, service_type_label: str) -> bool:
	if not parent_doc:
		return False
	fieldname = _parent_ij_fieldname(getattr(parent_doc, "doctype", None) or "")
	if not fieldname:
		return False
	for row in getattr(parent_doc, fieldname, None) or []:
		if not sales_quote_charge_service_types_equal(
			_row_val(row, "service_type"), service_type_label
		):
			continue
		if _ij_rows_same_identity(row, ij_row):
			return True
		if _quote_ij_rows_match_candidate(row, ij_row, service_type_label):
			return True
	return False


def _quote_has_matching_ij_row(sq_name: str, ij_row: Any, service_type_label: str) -> bool:
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return False
	meta = frappe.get_meta("Sales Quote")
	if not meta.get_field("internal_job_details"):
		return False
	sq_doc = frappe.get_cached_doc("Sales Quote", sq_name)
	rows = sq_doc.get("internal_job_details") or []
	if not rows:
		return False
	for row in rows:
		if _quote_ij_rows_match_candidate(row, ij_row, service_type_label):
			return True
	return False


def has_matching_internal_job_setup(
	sales_quote: str | None,
	parent_doc: Any | None,
	ij_row: Any,
	service_type_label: str,
) -> bool:
	"""True when *ij_row* is registered on the quote/parent and its parameters match charges."""
	if not ij_row:
		return False

	st = (service_type_label or (_row_val(ij_row, "service_type") or "")).strip()
	if not st:
		return False

	if not internal_job_matches_charges(sales_quote, parent_doc, ij_row, st):
		return False

	sq_name = _resolve_sales_quote_name(sales_quote, parent_doc)
	if sq_name and frappe.db.exists("Sales Quote", sq_name):
		sq_meta = frappe.get_meta("Sales Quote")
		if sq_meta.get_field("internal_job_details"):
			sq_rows = frappe.get_cached_doc("Sales Quote", sq_name).get("internal_job_details") or []
			if sq_rows:
				return _quote_has_matching_ij_row(sq_name, ij_row, st)

	return _parent_has_ij_row(parent_doc, ij_row, st)


def _eligibility_message(
	has_charges: bool,
	has_matching_ij: bool,
	service_type_label: str,
	parent_doc: Any | None = None,
) -> str | None:
	st = (service_type_label or "").strip() or _("this service")
	parent_dt = getattr(parent_doc, "doctype", None) or ""
	uses_lifecycle = _parent_uses_lifecycle_jobs(parent_doc)
	uses_services_tab = parent_dt in ("Special Project", "MICE Project")
	if has_charges and has_matching_ij:
		return None
	if not has_charges and not has_matching_ij:
		if uses_services_tab:
			return _(
				"Add charge lines for {0} on the Sales Quote (or programme) and define a matching Services row on the Services tab before creating."
			).format(st)
		if uses_lifecycle:
			return _(
				"Add charge lines for {0} on the Sales Quote (or programme) and define a matching Lifecycle Job on the Lifecycle tab before creating."
			).format(st)
		return _(
			"Add charge lines for {0} on the Sales Quote (or programme) and define a matching Internal Job on the Internal Jobs tab before creating."
		).format(st)
	if not has_charges:
		return _("Add charge lines for {0} on the Sales Quote before creating this internal job.").format(
			st
		)
	if uses_services_tab:
		return _(
			"Define a matching Services row for {0} on the Services tab before creating."
		).format(st)
	if uses_lifecycle:
		return _(
			"Define a matching Lifecycle Job for {0} on the Lifecycle tab before creating."
		).format(st)
	return _("Define a matching Internal Job for {0} on the Internal Jobs tab before creating.").format(
		st
	)


def evaluate_internal_job_creation_eligibility(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	ij_row: Any | None = None,
	service_type_label: str | None = None,
) -> dict[str, Any]:
	"""Return eligibility flags and a user-facing block message when not allowed."""
	st = (service_type_label or (_row_val(ij_row, "service_type") if ij_row else "") or "").strip()
	has_charges = charges_exist_for_service(sales_quote, parent_doc, st)
	has_matching_ij = has_matching_internal_job_setup(sales_quote, parent_doc, ij_row, st)
	eligible = bool(has_charges and has_matching_ij)
	return {
		"eligible": eligible,
		"has_charges": has_charges,
		"has_matching_ij": has_matching_ij,
		"message": _eligibility_message(has_charges, has_matching_ij, st, parent_doc),
	}


def _sales_quote_linked_service_rows(sq_doc: Any) -> list[Any]:
	"""Return Sales Quote linked-service rows.

	Sales Quote ``linked_services`` is a virtual desk grid backed by ``Linked Service``
	documents. ``Document.get("linked_services")`` reads the cleared ``__dict__`` cache
	(after save) and returns an empty list even when linked services exist — always use
	:func:`linked_service_rows` (or the ``linked_services`` property) instead.
	"""
	return linked_service_rows(sq_doc)


def _quote_has_matching_linked_service_row(
	sq_name: str, linked_service_doc: Any, service_type_label: str
) -> bool:
	"""True when the Sales Quote ``linked_services`` grid has a row matching *linked_service_doc*."""
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return False
	meta = frappe.get_meta("Sales Quote")
	if not meta.get_field("linked_services"):
		return True
	sq_doc = frappe.get_cached_doc("Sales Quote", sq_name)
	ls_name = (_row_val(linked_service_doc, "name") or "").strip()
	for row in _sales_quote_linked_service_rows(sq_doc):
		row_ls = (_row_val(row, "linked_service") or _row_val(row, "internal_job") or "").strip()
		if ls_name and row_ls == ls_name:
			return True
		if _quote_ij_rows_match_candidate(row, linked_service_doc, service_type_label):
			return True
	return False


def evaluate_linked_service_internal_job_eligibility(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	linked_service_doc: Any | None = None,
	service_type_label: str | None = None,
) -> dict[str, Any]:
	"""Eligibility for Create Internal Job when parameters come from a Linked Service document."""
	st = (
		service_type_label
		or (_row_val(linked_service_doc, "service_type") if linked_service_doc else "")
		or ""
	).strip()
	if not linked_service_doc:
		return {
			"eligible": False,
			"has_charges": False,
			"has_matching_ij": False,
			"message": _(
				"Linked charge line has no Linked Service link; parameters cannot be validated."
			),
		}
	has_charges = charges_exist_for_service(sales_quote, parent_doc, st)
	params_match = internal_job_matches_charges(sales_quote, parent_doc, linked_service_doc, st)
	has_matching_ls = params_match
	sq_name = _resolve_sales_quote_name(sales_quote, parent_doc)
	if has_matching_ls and sq_name and frappe.db.exists("Sales Quote", sq_name):
		has_matching_ls = _quote_has_matching_linked_service_row(sq_name, linked_service_doc, st)
	eligible = bool(has_charges and has_matching_ls)
	message = None
	if not eligible:
		if not has_charges:
			message = _(
				"Add charge lines for {0} on the Sales Quote before creating this internal job."
			).format(st or _("this service"))
		elif not params_match:
			message = _(
				"Linked Service parameters for {0} do not match any charge line on the Sales Quote."
			).format(st or _("this service"))
		else:
			message = _(
				"No matching Linked Service for {0} was found on the Sales Quote."
			).format(st or _("this service"))
	return {
		"eligible": eligible,
		"has_charges": has_charges,
		"has_matching_ij": has_matching_ls,
		"message": message,
	}


def require_linked_service_internal_job_eligible(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	linked_service_doc: Any | None = None,
	service_type_label: str | None = None,
) -> None:
	"""Throw when linked-service internal job creation is not allowed."""
	result = evaluate_linked_service_internal_job_eligibility(
		sales_quote=sales_quote,
		parent_doc=parent_doc,
		linked_service_doc=linked_service_doc,
		service_type_label=service_type_label,
	)
	if not result.get("eligible"):
		frappe.throw(
			result.get("message")
			or _("Cannot create internal job for this service."),
			title=_("Cannot create internal job"),
		)


def require_internal_job_creation_eligible(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	ij_row: Any | None = None,
	service_type_label: str | None = None,
) -> None:
	"""Throw when internal job creation is not allowed."""
	result = evaluate_internal_job_creation_eligibility(
		sales_quote=sales_quote,
		parent_doc=parent_doc,
		ij_row=ij_row,
		service_type_label=service_type_label,
	)
	if not result.get("eligible"):
		frappe.throw(
			result.get("message")
			or _("Cannot create internal job for this service."),
			title=_("Cannot create internal job"),
		)


def require_internal_job_eligibility_for_create(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	ij_row: Any | None = None,
	linked_service_doc: Any | None = None,
	service_type_label: str | None = None,
	uses_linked_charge_create: bool = False,
) -> None:
	"""Throw when internal job creation is not allowed (linked-service or legacy path)."""
	result = evaluate_internal_job_eligibility_for_create(
		sales_quote=sales_quote,
		parent_doc=parent_doc,
		ij_row=ij_row,
		linked_service_doc=linked_service_doc,
		service_type_label=service_type_label,
		uses_linked_charge_create=uses_linked_charge_create,
	)
	if not result.get("eligible"):
		frappe.throw(
			result.get("message")
			or _("Cannot create internal job for this service."),
			title=_("Cannot create internal job"),
		)


def _linked_service_doc_from_row(row: Any) -> Any | None:
	"""Load the Linked Service document referenced by a charge or planning row."""
	if not row:
		return None
	from logistics.utils.linked_service_compat import linked_service_doctype, row_linked_service_link

	ls = row_linked_service_link(row)
	if not ls or not frappe.db.exists(linked_service_doctype(), ls):
		return None
	return frappe.get_cached_doc(linked_service_doctype(), ls)


def evaluate_internal_job_eligibility_for_create(
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	ij_row: Any | None = None,
	linked_service_doc: Any | None = None,
	service_type_label: str | None = None,
	uses_linked_charge_create: bool = False,
) -> dict[str, Any]:
	"""Route eligibility to linked-service or legacy Internal Job Detail checks."""
	if uses_linked_charge_create:
		ls_doc = linked_service_doc or _linked_service_doc_from_row(ij_row)
		return evaluate_linked_service_internal_job_eligibility(
			sales_quote=sales_quote,
			parent_doc=parent_doc,
			linked_service_doc=ls_doc,
			service_type_label=service_type_label,
		)
	return evaluate_internal_job_creation_eligibility(
		sales_quote=sales_quote,
		parent_doc=parent_doc,
		ij_row=ij_row,
		service_type_label=service_type_label,
	)


def apply_eligibility_to_preview_flags(
	preview: dict[str, Any],
	*,
	sales_quote: str | None = None,
	parent_doc: Any | None = None,
	ij_row: Any | None = None,
	service_type_label: str | None = None,
	uses_linked_charge_create: bool = False,
	linked_service_doc: Any | None = None,
) -> dict[str, Any]:
	"""Merge eligibility into a preview/choice dict (sets creatable + not_creatable_message)."""
	if preview.get("creatable") is False:
		return preview
	result = evaluate_internal_job_eligibility_for_create(
		sales_quote=sales_quote,
		parent_doc=parent_doc,
		ij_row=ij_row,
		linked_service_doc=linked_service_doc,
		service_type_label=service_type_label,
		uses_linked_charge_create=uses_linked_charge_create,
	)
	if not result.get("eligible"):
		preview["creatable"] = False
		msg = result.get("message")
		if msg:
			preview["not_creatable_message"] = msg
	return preview
