# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Copy ``item_code`` onto the Item **Accounting Dimension** field on each invoice line
so ERPNext ``get_gl_dict`` posts that value on GL Entry (profitability "Dimension Item").

ERPNext already maps ``item.get(dimension)`` onto GL rows in
``accounts_controller.get_gl_dict`` when ``item`` is the SI/PI item row.
"""

from __future__ import unicode_literals

import frappe

from logistics.job_management.gl_item_dimension import get_item_accounting_dimension_fieldname_on_child_doctype


def _sync_items_table(doc, child_doctype, items_field="items"):
	fn = get_item_accounting_dimension_fieldname_on_child_doctype(child_doctype)
	if not fn:
		return
	for row in doc.get(items_field) or []:
		item_code = getattr(row, "item_code", None)
		if not item_code:
			continue
		setattr(row, fn, item_code)


def sync_item_accounting_dimension_from_invoice_items(doc, method=None):
	"""Hook: validate / before_submit / before_update_after_submit on Sales & Purchase Invoice."""
	if doc.doctype == "Sales Invoice":
		_sync_items_table(doc, "Sales Invoice Item", "items")
	elif doc.doctype == "Purchase Invoice":
		_sync_items_table(doc, "Purchase Invoice Item", "items")
