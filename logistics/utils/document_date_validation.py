import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, today

from logistics.utils.validation_user_messages import (
	planned_date_range_invalid_message,
	planned_date_range_title,
	planned_window_before_reference_warning_message,
	planned_window_before_reference_warning_title,
)


def throw_if_left_date_after_right(left_value, right_value, message_getter, title_getter):
	"""Throw when both values exist and the left date is after the right date."""
	if not left_value or not right_value:
		return
	if getdate(left_value) > getdate(right_value):
		frappe.throw(message_getter(), title=title_getter())


def throw_if_start_after_end(
	start_value,
	end_value,
	message_getter,
	title_getter,
	*,
	use_datetime=False,
):
	"""Throw when both values exist and start is after end (date or datetime)."""
	if not start_value or not end_value:
		return
	if use_datetime:
		if get_datetime(start_value) > get_datetime(end_value):
			frappe.throw(message_getter(), title=title_getter())
	elif getdate(start_value) > getdate(end_value):
		frappe.throw(message_getter(), title=title_getter())


def validate_planned_date_range(
	doc,
	start_field="planned_start",
	end_field="planned_end",
	*,
	use_datetime=False,
	message_getter=None,
	title_getter=None,
):
	"""Hard-block when Planned Start is after Planned End (both must be set)."""
	if not doc:
		return
	throw_if_start_after_end(
		doc.get(start_field),
		doc.get(end_field),
		message_getter or planned_date_range_invalid_message,
		title_getter or planned_date_range_title,
		use_datetime=use_datetime,
	)


def warn_if_planned_end_before_reference(
	doc,
	reference_field=None,
	*,
	reference_value=None,
	reference_label=None,
):
	"""Soft-warn when Planned End is before a reference date (e.g. quote date)."""
	if not doc:
		return
	planned_end = doc.get("planned_end")
	ref = reference_value
	if ref is None and reference_field:
		ref = doc.get(reference_field)
	if not planned_end or not ref:
		return
	if getdate(planned_end) >= getdate(ref):
		return

	label = reference_label or _(
		(reference_field or "reference").replace("_", " ").title()
	)
	message = planned_window_before_reference_warning_message(label, getdate(ref))
	cache = getattr(frappe.flags, "_planned_window_warnings_shown", None)
	if cache is None:
		cache = set()
		frappe.flags._planned_window_warnings_shown = cache
	if message in cache:
		return
	cache.add(message)
	frappe.msgprint(
		message,
		title=planned_window_before_reference_warning_title(),
		indicator="orange",
		alert=True,
	)


def is_future_date(value):
	"""Return True when value is a date greater than today."""
	if not value:
		return False
	return getdate(value) > getdate(today())


def throw_if_not_past_date(value, status_label, date_label, title):
	"""Require date to exist and be in the past for status-specific checks."""
	if not value:
		frappe.throw(
			frappe._("Status '{0}' requires {1} to be set.").format(status_label, date_label),
			title=title,
		)
	if getdate(value) >= getdate(today()):
		frappe.throw(
			frappe._("Status '{0}' is only valid when {1} ({2}) has passed.").format(
				status_label,
				date_label,
				value,
			),
			title=title,
		)
