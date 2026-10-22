# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe

from logistics.job_management.beginning_jobs import create_beginning_jobs


@frappe.whitelist()
def create_beginning_job(payload):
	"""Desk entry point for the Beginning Jobs page."""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)
	return create_beginning_jobs(payload)
