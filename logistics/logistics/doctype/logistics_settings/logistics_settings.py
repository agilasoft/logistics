# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class LogisticsSettings(Document):
	def validate(self):
		"""Validate temperature limits configuration"""
		self.validate_temperature_limits()
	
	def validate_temperature_limits(self):
		"""Validate that min_temp < max_temp if both are set"""
		min_temp = flt(getattr(self, "min_temp", None)) if hasattr(self, "min_temp") else None
		max_temp = flt(getattr(self, "max_temp", None)) if hasattr(self, "max_temp") else None
		
		if min_temp is not None and max_temp is not None:
			if min_temp >= max_temp:
				frappe.throw(
					_("Minimum temperature ({0}°C) must be less than maximum temperature ({1}°C).").format(
						min_temp, max_temp
					),
					title=_("Temperature Limits Validation Error")
				)