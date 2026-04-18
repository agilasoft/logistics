# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


_EVENT_TO_LEGACY = {
	"Customer Receipt": "Customer Deposit",
	"Pay Carrier": "Carrier Deposit",
	"Refund From Carrier": "Refund",
	"Refund To Customer": "Refund",
	"Forfeit": "Refund",
}


class ContainerDeposit(Document):
	def validate(self):
		self._sync_legacy_deposit_type()
		self._require_job_number()
		self._validate_amounts_for_event()

	def _sync_legacy_deposit_type(self):
		ev = self.get("event_type") or "Pay Carrier"
		self.event_type = ev
		self.deposit_type = _EVENT_TO_LEGACY.get(ev, "Carrier Deposit")

	def _require_job_number(self):
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return
		try:
			settings = frappe.get_single("Logistics Settings")
		except Exception:
			return
		if not settings.get("require_job_number_on_container_deposits"):
			return
		if flt(self.deposit_amount) <= 0 and flt(self.refund_amount) <= 0:
			return
		if not self.get("job_number"):
			frappe.throw(_("Job Number is required on this deposit line."), title=_("Container deposit"))

	def _validate_amounts_for_event(self):
		ev = self.get("event_type") or ""
		if ev in ("Refund From Carrier", "Refund To Customer") and flt(self.refund_amount) < 0:
			frappe.throw(_("Refund amount cannot be negative."), title=_("Container deposit"))
		if ev in ("Customer Receipt", "Pay Carrier") and flt(self.deposit_amount) < 0:
			frappe.throw(_("Deposit amount cannot be negative."), title=_("Container deposit"))
