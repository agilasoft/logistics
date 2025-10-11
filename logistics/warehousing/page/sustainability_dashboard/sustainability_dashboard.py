# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
	"""Get context for sustainability dashboard page"""
	context.title = _("Sustainability Dashboard")
	context.no_cache = 1
	
	# Get default filters
	context.default_site = frappe.get_value("Warehouse Settings", "Warehouse Settings", "default_site")
	context.default_facility = frappe.get_value("Warehouse Settings", "Warehouse Settings", "default_facility")
	
	# Get available sites and facilities
	context.sites = frappe.get_all("Storage Location Configurator", 
		filters={"level": "Site"}, 
		fields=["name", "title"]
	)
	
	context.facilities = frappe.get_all("Storage Location Configurator", 
		filters={"level": "Building"}, 
		fields=["name", "title"]
	)
	
	# Get sustainability data
	context.sustainability_data = get_sustainability_dashboard_data()
	
	return context


def get_sustainability_dashboard_data():
	"""Get sustainability dashboard data"""
	try:
		from logistics.warehousing.sustainability_dashboard import get_sustainability_dashboard_data
		return get_sustainability_dashboard_data()
	except ImportError:
		return {
			"energy_data": {"summary": {}},
			"carbon_data": {"summary": {}},
			"green_metrics": {},
			"sustainability_scores": {},
			"trends": {}
		}
