# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuotePack(Document):
	def validate(self):
		self._validate_unique_quotes()
		self._sync_quote_pack_links()
		self._calculate_total()

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
