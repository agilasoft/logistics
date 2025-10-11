# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days


class GreenCertification(Document):
	def before_save(self):
		"""Validate certification dates and set default expiry if not provided"""
		self.validate_certification_dates()
		self.set_default_expiry_date()
	
	def validate_certification_dates(self):
		"""Validate that certification date is not in the future and expiry is after certification"""
		if self.certification_date and getdate(self.certification_date) > getdate():
			frappe.throw("Certification date cannot be in the future")
		
		if self.certification_date and self.expiry_date:
			if getdate(self.expiry_date) <= getdate(self.certification_date):
				frappe.throw("Expiry date must be after certification date")
	
	def set_default_expiry_date(self):
		"""Set default expiry date if not provided (typically 3 years from certification)"""
		if self.certification_date and not self.expiry_date:
			self.expiry_date = add_days(self.certification_date, 1095)  # 3 years
	
	def is_certification_valid(self):
		"""Check if certification is currently valid"""
		if not self.certification_date or not self.expiry_date:
			return False
		
		today = getdate()
		return getdate(self.certification_date) <= today <= getdate(self.expiry_date)
	
	def get_certification_score(self):
		"""Get certification score based on level and type"""
		level_scores = {
			"Platinum": 100,
			"Gold": 85,
			"Silver": 70,
			"Bronze": 55,
			"Certified": 40,
			"Basic": 25
		}
		
		type_multipliers = {
			"Energy Efficiency": 1.2,
			"Carbon Neutral": 1.5,
			"LEED": 1.3,
			"BREEAM": 1.3,
			"ISO 14001": 1.1,
			"Green Building": 1.2,
			"Renewable Energy": 1.4,
			"Other": 1.0
		}
		
		base_score = level_scores.get(self.certification_level, 0)
		multiplier = type_multipliers.get(self.certification_type, 1.0)
		
		return base_score * multiplier
