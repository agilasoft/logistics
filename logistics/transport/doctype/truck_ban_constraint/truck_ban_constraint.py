# Copyright (c) 2024, logistics and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_time


CONSTRAINT_TYPES = frozenset(
	{
		"Area Ban",
		"Route Ban",
		"Time-Based Ban",
		"Weight-Based Ban",
		"Vehicle Type Ban",
		"Plate Coding",
	}
)


class TruckBanConstraint(Document):
	def validate(self):
		self._validate_constraint_type()
		self._validate_type_requirements()
		self._validate_plate_coding_rows()

	def _validate_constraint_type(self):
		if not self.constraint_type:
			frappe.throw(_("Constraint Type is required"))
		if self.constraint_type not in CONSTRAINT_TYPES:
			frappe.throw(
				_("Constraint Type must be one of: {0}").format(", ".join(sorted(CONSTRAINT_TYPES)))
			)

	def _validate_type_requirements(self):
		ctype = self.constraint_type
		if ctype == "Area Ban" and not (self.get("restricted_addresses") or []):
			frappe.throw(_("Area Ban requires at least one Restricted Address/Area"))
		if ctype == "Route Ban" and not (self.get("restricted_routes") or []):
			frappe.throw(_("Route Ban requires at least one Restricted Route"))
		if ctype == "Plate Coding" and not (self.get("plate_coding") or []):
			frappe.throw(_("Plate Coding requires at least one Plate Coding row"))
		if ctype == "Vehicle Type Ban" and not (self.get("restricted_vehicle_types") or []):
			frappe.throw(_("Vehicle Type Ban requires at least one Restricted Vehicle Type"))
		if ctype == "Weight-Based Ban" and flt(self.min_vehicle_weight_restriction) <= 0:
			frappe.throw(_("Weight-Based Ban requires Minimum Vehicle Weight (kg) greater than 0"))
		if ctype != "Plate Coding" and not self.all_day:
			if not self.start_time or not self.end_time:
				frappe.throw(_("Start Time and End Time are required when All Day is unchecked"))

	def _validate_plate_coding_rows(self):
		if self.constraint_type != "Plate Coding":
			return
		for row in self.get("plate_coding") or []:
			digit = row.restricted_digit
			if digit is None or digit < 0 or digit > 9:
				frappe.throw(
					_("Plate Coding row {0}: Restricted Digit must be an integer from 0 to 9").format(
						row.idx
					)
				)
			if not row.ban_start or not row.ban_end:
				continue
			if get_time(row.ban_start) > get_time(row.ban_end):
				frappe.throw(
					_("Plate Coding row {0}: Ban Start must be on or before Ban End").format(row.idx)
				)
