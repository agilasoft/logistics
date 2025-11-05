# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate
from frappe import _


class EmissionFactors(Document):
	def before_save(self):
		"""Validate data before saving"""
		self.validate_data()
	
	def validate_data(self):
		"""Validate emission factor data"""
		# Validate factor value is positive
		if self.factor_value and self.factor_value <= 0:
			frappe.throw(_("Factor value must be positive"))
		
		# Validate date range
		if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
			frappe.throw(_("Valid From date cannot be after Valid To date"))
		
		# Validate date is not in the future
		if self.valid_from and self.valid_from > getdate():
			frappe.throw(_("Valid From date cannot be in the future"))
	
	def is_valid_for_date(self, date):
		"""Check if emission factor is valid for a given date"""
		if not self.is_active:
			return False
		
		if self.valid_from and date < self.valid_from:
			return False
		
		if self.valid_to and date > self.valid_to:
			return False
		
		return True
	
	def increment_usage_count(self):
		"""Increment usage count when factor is used"""
		self.usage_count = (self.usage_count or 0) + 1
		self.save(ignore_permissions=True)


@frappe.whitelist()
def get_emission_factor(factor_name, date=None, module=None):
	"""Get emission factor by name for a specific date and module"""
	if not date:
		date = getdate()
	
	filters = {
		"factor_name": factor_name,
		"is_active": 1
	}
	
	if module and module != "All":
		filters["module"] = ["in", [module, "All"]]
	
	# Get all matching factors
	factors = frappe.get_all("Emission Factors",
		filters=filters,
		fields=["*"],
		order_by="valid_from desc, creation desc"
	)
	
	# Find the most appropriate factor for the date
	for factor in factors:
		if factor.valid_from and date < factor.valid_from:
			continue
		if factor.valid_to and date > factor.valid_to:
			continue
		
		# Increment usage count
		factor_doc = frappe.get_doc("Emission Factors", factor.name)
		factor_doc.increment_usage_count()
		
		return factor
	
	return None


@frappe.whitelist()
def get_emission_factors_by_category(category, date=None, module=None):
	"""Get all emission factors for a specific category"""
	if not date:
		date = getdate()
	
	filters = {
		"category": category,
		"is_active": 1
	}
	
	if module and module != "All":
		filters["module"] = ["in", [module, "All"]]
	
	# Get all matching factors
	factors = frappe.get_all("Emission Factors",
		filters=filters,
		fields=["*"],
		order_by="valid_from desc, creation desc"
	)
	
	# Filter by date validity
	valid_factors = []
	for factor in factors:
		if factor.valid_from and date < factor.valid_from:
			continue
		if factor.valid_to and date > factor.valid_to:
			continue
		valid_factors.append(factor)
	
	return valid_factors


@frappe.whitelist()
def create_emission_factor(factor_name, factor_value, unit_of_measure, scope, category, **kwargs):
	"""Create a new emission factor"""
	
	doc = frappe.new_doc("Emission Factors")
	doc.factor_name = factor_name
	doc.factor_value = flt(factor_value)
	doc.unit_of_measure = unit_of_measure
	doc.scope = scope
	doc.category = category
	doc.module = kwargs.get("module", "All")
	doc.source = kwargs.get("source")
	doc.reference = kwargs.get("reference")
	doc.valid_from = kwargs.get("valid_from")
	doc.valid_to = kwargs.get("valid_to")
	doc.description = kwargs.get("description")
	doc.is_active = kwargs.get("is_active", 1)
	
	doc.insert(ignore_permissions=True)
	return doc.name
