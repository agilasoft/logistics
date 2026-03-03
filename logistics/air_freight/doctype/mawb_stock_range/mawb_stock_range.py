# -*- coding: utf-8 -*-
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _


class MAWBStockRange(Document):
	def validate(self):
		self.validate_serial_range()
		if not self.next_serial and self.from_serial is not None:
			self.next_serial = self.from_serial
		self.update_computed_fields()

	def validate_serial_range(self):
		if self.from_serial is None or self.to_serial is None:
			return
		if self.from_serial > self.to_serial:
			frappe.throw(_("From Serial cannot be greater than To Serial."))
		if self.next_serial is not None:
			if self.next_serial < self.from_serial or self.next_serial > self.to_serial:
				frappe.throw(_("Next Serial must be between From Serial and To Serial."))

	def update_computed_fields(self):
		"""Set available count and status for display."""
		if self.next_serial is not None and self.to_serial is not None:
			self.available_count = max(0, self.to_serial - self.next_serial + 1)
			if self.available_count == 0:
				self.stock_status = "Exhausted"
			elif self.available_count <= 100:
				self.stock_status = "Low"
			else:
				self.stock_status = "Available"
		else:
			self.available_count = 0
			self.stock_status = ""


def get_default_mawb_stock_range(company=None):
	"""Return the default MAWB Stock Range for the company or any default."""
	filters = {"is_default": 1}
	if company:
		filters["company"] = ["in", [company, ""]]
	ranges = frappe.get_all(
		"MAWB Stock Range",
		filters=filters,
		fields=["name", "company"],
		limit=2
	)
	if ranges:
		# Prefer company-specific default
		for r in ranges:
			if r.get("company") == company:
				return r["name"]
		return ranges[0]["name"]
	return None


@frappe.whitelist()
def issue_mawb_from_stock(airline=None, stock_range_name=None, company=None, **mawb_defaults):
	"""
	Consume the next MAWB number from the given or default stock range,
	create a Master Air Waybill with that number, and return its name.

	:param airline: Optional airline link; used to pick a range if stock_range_name not given.
	:param stock_range_name: Optional name of MAWB Stock Range to use.
	:param company: Optional company for default range lookup.
	:param mawb_defaults: Optional dict of field values for the new Master Air Waybill (e.g. origin_airport, destination_airport, flight_date).
	:return: dict with mawb_name, master_awb_no, stock_range
	"""
	if not stock_range_name:
		stock_range_name = get_default_mawb_stock_range(company)
		if not stock_range_name and airline:
			# Fallback: any range for this airline
			ranges = frappe.get_all(
				"MAWB Stock Range",
				filters={"airline": airline},
				fields=["name"],
				limit=1
			)
			if ranges:
				stock_range_name = ranges[0]["name"]
		if not stock_range_name:
			frappe.throw(_("No MAWB Stock Range found. Create a range or pass stock_range_name."))

	# Lock the row and get next serial to avoid double-issue
	row = frappe.db.sql(
		"""SELECT next_serial, `to_serial`, prefix, airline
		   FROM `tabMAWB Stock Range` WHERE name = %s FOR UPDATE""",
		(stock_range_name,),
		as_dict=True
	)
	if not row:
		frappe.throw(_("MAWB Stock Range {0} not found.").format(stock_range_name))
	row = row[0]
	serial = row.next_serial
	if serial > row.to_serial:
		frappe.throw(_("MAWB stock exhausted for range {0}.").format(stock_range_name))

	# Consume the number in the same transaction (before insert commits)
	frappe.db.sql(
		"UPDATE `tabMAWB Stock Range` SET next_serial = %s WHERE name = %s",
		(serial + 1, stock_range_name)
	)

	# Format: prefix + 8-digit serial (e.g. 176-12345678)
	master_awb_no = "{0}-{1:08d}".format(
		str(row.prefix).zfill(3),
		serial
	)

	# Create Master Air Waybill (name will be master_awb_no due to autoname); commit happens here
	mawb = frappe.new_doc("Master Air Waybill")
	mawb.master_awb_no = master_awb_no
	mawb.airline = row.airline
	if mawb_defaults:
		for key, value in mawb_defaults.items():
			if hasattr(mawb, key) and value is not None:
				mawb.set(key, value)
	mawb.issued_from_stock = 1
	mawb.mawb_stock_range = stock_range_name
	mawb.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"mawb_name": mawb.name,
		"master_awb_no": master_awb_no,
		"stock_range": stock_range_name,
	}
