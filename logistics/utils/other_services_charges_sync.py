# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Other Services are auxiliary/incidental charges entered in the Charges tab with the
'Other Services' checkbox. This module provides validation for Other Service items."""

from __future__ import unicode_literals

import frappe
from frappe import _


def is_item_other_service(item_code):
	"""Check if item_code is an Other Service item (Item.custom_is_other_service = 1)."""
	if not item_code:
		return False
	return frappe.db.get_value("Item", item_code, "custom_is_other_service") == 1


def validate_charge_item_not_manual_other_service(charge_row, charges_doctype, item_field="item_code"):
	"""Validate that a charge row with an Other Service item has 'Other Services' checked."""
	item_code = getattr(charge_row, item_field, None)
	if not item_code:
		return
	if not is_item_other_service(item_code):
		return
	# Allow if already marked as other services
	if (
		getattr(charge_row, "is_other_service", 0)
		or getattr(charge_row, "other_service_reference", None)
		or getattr(charge_row, "other_service_reference_no", None)
	):
		return
	frappe.throw(
		_("Item {0} is an Other Service item. Add it in the Charges tab and check 'Other Services' on the row.").format(
			item_code
		),
		title=_("Other Service Item"),
	)
