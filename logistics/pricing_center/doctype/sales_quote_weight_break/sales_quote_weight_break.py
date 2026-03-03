# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SalesQuoteWeightBreak(Document):
	pass


@frappe.whitelist()
def save_weight_breaks_for_reference(reference_doctype, reference_no, weight_breaks, record_type):
	"""
	Save weight break records for any doctype (Sales Quote Air Freight, Air Booking Charges, etc.)

	Args:
		reference_doctype: DocType being referenced (e.g. 'Sales Quote Air Freight', 'Air Booking Charges')
		reference_no: Name of the referenced document
		weight_breaks: List of dicts with rate_type, weight_break, unit_rate
		record_type: 'Selling' or 'Cost'

	Returns:
		dict with success and optional error
	"""
	try:
		if not reference_doctype or not reference_no:
			return {'success': False, 'error': 'Reference doctype and reference no are required'}

		if isinstance(weight_breaks, str):
			weight_breaks = json.loads(weight_breaks) if weight_breaks else []

		# Delete existing weight breaks for this reference and type
		frappe.db.delete(
			'Sales Quote Weight Break',
			{'reference_doctype': reference_doctype, 'reference_no': reference_no, 'type': record_type}
		)

		# Create new records
		for wb in (weight_breaks or []):
			if not wb.get('weight_break') and not wb.get('unit_rate'):
				continue
			doc = frappe.new_doc('Sales Quote Weight Break')
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.rate_type = wb.get('rate_type') or 'N (Normal)'
			doc.weight_break = flt(wb.get('weight_break', 0))
			doc.unit_rate = flt(wb.get('unit_rate', 0))
			doc.currency = wb.get('currency') or 'USD'
			doc.insert(ignore_permissions=True)

		frappe.db.commit()
		return {'success': True}
	except Exception as e:
		frappe.log_error(f"Error saving weight breaks: {str(e)}")
		return {'success': False, 'error': str(e)}


@frappe.whitelist()
def get_weight_breaks(reference_doctype, reference_no, record_type='Selling'):
	"""
	Get list of weight break records for a reference (for dialog editing).

	Args:
		reference_doctype: DocType being referenced (e.g. 'Sales Quote Air Freight', 'Sales Quote Sea Freight')
		reference_no: Name of the referenced document (child row name)
		record_type: 'Selling' or 'Cost'

	Returns:
		dict with success and weight_breaks list
	"""
	try:
		if not reference_doctype or not reference_no:
			return {'success': False, 'weight_breaks': []}

		weight_breaks = frappe.get_all(
			'Sales Quote Weight Break',
			filters={
				'reference_doctype': reference_doctype,
				'reference_no': reference_no,
				'type': record_type
			},
			fields=['rate_type', 'weight_break', 'unit_rate', 'currency'],
			order_by='weight_break asc'
		)
		return {'success': True, 'weight_breaks': weight_breaks or []}
	except Exception as e:
		frappe.log_error(f"Error getting weight breaks: {str(e)}")
		return {'success': False, 'weight_breaks': []}


@frappe.whitelist()
def get_weight_break_html(reference_doctype, reference_no, record_type='Selling'):
	"""
	Get HTML representation of weight break rates for any doctype.

	Args:
		reference_doctype: DocType being referenced
		reference_no: Name of the referenced document
		record_type: 'Selling' or 'Cost'

	Returns:
		dict with success and html
	"""
	try:
		if not reference_doctype or not reference_no:
			return {'success': False, 'html': ''}

		weight_breaks = frappe.get_all(
			'Sales Quote Weight Break',
			filters={
				'reference_doctype': reference_doctype,
				'reference_no': reference_no,
				'type': record_type
			},
			fields=['rate_type', 'weight_break', 'unit_rate', 'currency'],
			order_by='weight_break asc'
		)

		if not weight_breaks:
			return {'success': True, 'html': '<span class="text-muted">No weight breaks defined</span>'}

		html = '<div class="weight-break-summary">'
		html += '<table class="table table-condensed table-bordered" style="margin: 0;">'
		html += '<thead><tr><th>Type</th><th>Weight Break</th><th>Unit Rate</th><th>Currency</th></tr></thead>'
		html += '<tbody>'
		for wb in weight_breaks:
			html += f'<tr><td>{wb.get("rate_type", "")}</td>'
			html += f'<td>{flt(wb.get("weight_break", 0))}</td>'
			html += f'<td>{flt(wb.get("unit_rate", 0))}</td>'
			html += f'<td>{wb.get("currency", "")}</td></tr>'
		html += '</tbody></table></div>'
		return {'success': True, 'html': html}
	except Exception as e:
		frappe.log_error(f"Error getting weight break HTML: {str(e)}")
		return {'success': False, 'html': f'<span class="text-danger">Error: {str(e)}</span>'}


@frappe.whitelist()
def refresh_weight_break_html_fields(reference_doctype, reference_no):
	"""
	Refresh weight break HTML for a referenced document.

	Returns:
		dict with success, selling_html, cost_html
	"""
	try:
		if not reference_doctype or not reference_no:
			return {'success': False, 'error': 'Reference required'}

		selling_result = get_weight_break_html(reference_doctype, reference_no, 'Selling')
		cost_result = get_weight_break_html(reference_doctype, reference_no, 'Cost')
		return {
			'success': True,
			'selling_html': selling_result.get('html', '') if selling_result.get('success') else '',
			'cost_html': cost_result.get('html', '') if cost_result.get('success') else ''
		}
	except Exception as e:
		frappe.log_error(f"Error refreshing weight break HTML: {str(e)}")
		return {'success': False, 'error': str(e)}
