# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class ManifestSettings(Document):
	def validate(self):
		"""Validate manifest settings"""
		# Validate that at least one country system is enabled
		if not self.enable_ca_emanifest and not self.enable_us_ams and not self.enable_us_isf and not self.enable_jp_afr:
			frappe.msgprint(
				_("At least one country filing system should be enabled."),
				indicator="orange",
				title=_("No System Enabled")
			)


def get_manifest_settings(company: str = None) -> dict:
	"""
	Get manifest settings for a company.
	
	Args:
		company: Company name. If not provided, uses default company.
		
	Returns:
		dict: Manifest settings document
	"""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	
	try:
		return frappe.get_doc("Manifest Settings", company)
	except frappe.DoesNotExistError:
		frappe.throw(_("Manifest Settings not found for company {0}. Please create Manifest Settings first.").format(company))

