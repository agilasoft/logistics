# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	return get_columns(), get_data(filters or {})


def get_columns():
	return [
		{"fieldname": "container", "label": _("Container"), "fieldtype": "Link", "options": "Container", "width": 160},
		{"fieldname": "container_number", "label": _("Container No"), "fieldtype": "Data", "width": 120},
		{"fieldname": "deposit_amount", "label": _("Deposit (header)"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "missing", "label": _("Missing requirements"), "fieldtype": "Data", "width": 280},
	]


def get_data(filters):
	out = []
	containers = frappe.get_all(
		"Container",
		filters=[["deposit_amount", ">", 0], ["return_status", "!=", "Returned"]],
		fields=["name", "container_number", "deposit_amount"],
	)
	for c in containers:
		doc = frappe.get_doc("Container", c.name)
		missing = _missing_mandatory(doc)
		if missing:
			out.append(
				{
					"container": doc.name,
					"container_number": doc.container_number,
					"deposit_amount": flt(doc.deposit_amount),
					"missing": ", ".join(missing),
				}
			)
	return out


def _missing_mandatory(doc):
	bad = []
	for line in doc.get("refund_readiness") or []:
		if not frappe.utils.cint(line.get("mandatory")):
			continue
		if line.status == "Received":
			continue
		if line.status == "Waived" and (line.waiver_reason or "").strip():
			continue
		bad.append(line.requirement_name or _("(unnamed)"))
	return bad
