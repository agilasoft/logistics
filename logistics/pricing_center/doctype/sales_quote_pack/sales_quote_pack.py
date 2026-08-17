# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuotePack(Document):
	def validate(self):
		self._validate_manual_accepted_status()
		self._validate_unique_quotes()
		self._validate_quote_customers()
		self._sync_quote_pack_links()
		self._calculate_total()

	def before_submit(self):
		self._submit_linked_sales_quotes()
		self.status = "Accepted"

	def before_cancel(self):
		# Set before db_update so Cancelled is persisted (on_cancel runs after save).
		self.status = "Cancelled"

	def on_cancel(self):
		# Child Sales Quotes keep sales_quote_pack; allow pack cancel despite that link.
		self.ignore_linked_doctypes = ["Sales Quote"]

	def _validate_manual_accepted_status(self):
		"""Accepted is set on Submit; block setting it on a draft save."""
		if (getattr(self, "status", None) or "").strip() != "Accepted":
			return
		# Only enforce on draft saves; submit/cancel paths set Accepted/Cancelled themselves.
		if int(getattr(self, "docstatus", 0) or 0) != 0:
			return
		if getattr(self, "_action", None) == "submit":
			return
		if getattr(self.flags, "ignore_accepted_status_check", False):
			return
		frappe.throw(
			_("Set Status to Accepted by submitting this Sales Quote Pack."),
			title=_("Submit Required"),
		)

	def _validate_unique_quotes(self):
		seen = set()
		for row in self.get("quotations") or []:
			sq = (row.sales_quote or "").strip()
			if not sq:
				continue
			if sq in seen:
				frappe.throw(_("Sales Quote {0} appears more than once in this pack.").format(sq))
			seen.add(sq)
			other = frappe.db.get_value("Sales Quote", sq, "sales_quote_pack")
			if other and other != self.name and not self.is_new():
				frappe.throw(
					_("Sales Quote {0} is already in pack {1}.").format(sq, other)
				)

	def _validate_quote_customers(self):
		if not self.customer:
			return
		for row in self.get("quotations") or []:
			sq = (row.sales_quote or "").strip()
			if not sq:
				continue
			quote_customer = frappe.db.get_value("Sales Quote", sq, "customer")
			if quote_customer and quote_customer != self.customer:
				frappe.throw(
					_("Sales Quote {0} belongs to customer {1}, not {2}.").format(
						sq, quote_customer, self.customer
					)
				)

	def _sync_quote_pack_links(self):
		if self.is_new():
			return
		old_quotes = set(
			frappe.get_all(
				"Sales Quote Pack Line",
				filters={"parent": self.name, "parenttype": "Sales Quote Pack"},
				pluck="sales_quote",
			)
		)
		new_quotes = {(row.sales_quote or "").strip() for row in self.get("quotations") or [] if row.sales_quote}
		for sq in old_quotes - new_quotes:
			if sq and frappe.db.get_value("Sales Quote", sq, "sales_quote_pack") == self.name:
				frappe.db.set_value("Sales Quote", sq, "sales_quote_pack", None)
		for row in self.get("quotations") or []:
			sq = (row.sales_quote or "").strip()
			if sq:
				frappe.db.set_value("Sales Quote", sq, "sales_quote_pack", self.name)

	def _calculate_total(self):
		total = 0.0
		for row in self.get("quotations") or []:
			if not cint_row(row, "include_in_total"):
				continue
			sq = (row.sales_quote or "").strip()
			if not sq:
				continue
			total += flt(_quote_charge_total(sq))
		self.total_amount = total

	def _linked_quote_names(self):
		names = []
		seen = set()
		for row in self.get("quotations") or []:
			sq = (row.sales_quote or "").strip()
			if not sq or sq in seen:
				continue
			seen.add(sq)
			names.append(sq)
		return names

	def _submit_linked_sales_quotes(self):
		names = self._linked_quote_names()
		if not names:
			frappe.throw(
				_("Add at least one Sales Quote before submitting this pack."),
				title=_("Quotations Required"),
			)

		errors = []
		to_submit = []
		for name in names:
			row = frappe.db.get_value("Sales Quote", name, ["name", "docstatus"], as_dict=True)
			if not row:
				errors.append(_("Sales Quote {0} was not found.").format(name))
				continue
			if int(row.docstatus or 0) == 1:
				continue
			if int(row.docstatus or 0) == 2:
				errors.append(_("Sales Quote {0} is cancelled; remove or replace it.").format(name))
				continue
			try:
				quote = frappe.get_doc("Sales Quote", name)
				quote.flags.submit_from_sales_quote_pack = True
				quote.run_method("before_submit")
				to_submit.append(name)
			except frappe.ValidationError as e:
				errors.append(_("Sales Quote {0}: {1}").format(name, str(e)))
			except Exception as e:
				errors.append(_("Sales Quote {0}: {1}").format(name, str(e)))

		if errors:
			frappe.throw(
				"<br>".join(errors),
				title=_("Cannot Submit Sales Quote Pack"),
			)

		submitted_now = []
		try:
			for name in to_submit:
				quote = frappe.get_doc("Sales Quote", name)
				if int(quote.docstatus or 0) == 1:
					continue
				quote.flags.submit_from_sales_quote_pack = True
				quote.submit()
				submitted_now.append(name)
		except Exception:
			for name in reversed(submitted_now):
				try:
					q = frappe.get_doc("Sales Quote", name)
					if int(q.docstatus or 0) == 1:
						q.cancel()
				except Exception:
					frappe.log_error(
						title="Sales Quote Pack submit rollback failed",
						message=frappe.get_traceback(),
					)
			raise


def cint_row(row, field):
	from frappe.utils import cint
	return cint(getattr(row, field, 0))


def _quote_charge_total(sales_quote_name: str) -> float:
	rows = frappe.get_all(
		"Sales Quote Charge",
		filters={"parent": sales_quote_name, "parenttype": "Sales Quote", "parentfield": "charges"},
		fields=["estimated_revenue"],
	)
	return sum(flt(r.estimated_revenue) for r in rows)


@frappe.whitelist()
def create_sales_quote_from_pack(pack_name: str):
	pack = frappe.get_doc("Sales Quote Pack", pack_name)
	quote = frappe.new_doc("Sales Quote")
	quote.customer = pack.customer
	quote.consignee = pack.consignee or pack.customer
	quote.shipper = pack.shipper or pack.customer
	quote.company = pack.company
	quote.branch = pack.branch
	quote.profit_center = pack.profit_center
	quote.cost_center = pack.cost_center
	quote.sales_rep = pack.sales_rep
	quote.operations_rep = pack.operations_rep
	quote.customer_service_rep = pack.customer_service_rep
	quote.quotation_type = "One-off"
	quote.sales_quote_pack = pack.name
	quote.insert()
	return quote.name
