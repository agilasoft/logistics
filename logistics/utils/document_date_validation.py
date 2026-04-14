import frappe
from frappe.utils import getdate, today


def throw_if_left_date_after_right(left_value, right_value, message_getter, title_getter):
	"""Throw when both values exist and the left date is after the right date."""
	if not left_value or not right_value:
		return
	if getdate(left_value) > getdate(right_value):
		frappe.throw(message_getter(), title=title_getter())


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
