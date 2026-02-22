# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared milestone HTML builder for Jobs, Shipments, and Declarations."""

from __future__ import unicode_literals

import frappe


def build_milestone_html(
	doctype,
	docname,
	origin_name,
	destination_name,
	detail_items,
	milestones,
	format_datetime_fn,
	origin_party_name="",
	origin_party_address="",
	destination_party_name="",
	destination_party_address="",
):
	"""
	Build milestone dashboard HTML.
	detail_items: list of (label, value) for header details.
	"""
	from logistics.document_management.api import get_document_alerts_html

	doc_alerts = get_document_alerts_html(doctype, docname or "new")

	# Get milestone details
	milestone_details = {}
	if milestones:
		milestone_names = [m.get("milestone") for m in milestones if m.get("milestone")]
		if milestone_names:
			milestone_data = frappe.get_all(
				"Logistics Milestone",
				filters={"name": ["in", milestone_names]},
				fields=["name", "description", "code"],
			)
			milestone_details = {m.name: m for m in milestone_data}

	# Build header
	detail_html = ""
	for label, value in (detail_items or []):
		if value:
			detail_html += f'<div class="detail-item"><label>{label}:</label><span>{value}</span></div>'

	html = f"""
		<div class="job-header">
			<div class="header-main">
				<div class="header-column">
					<div class="header-section">
						<label class="section-label">ORIGIN</label>
						<div class="location-name">{origin_name or "Origin"}</div>
					</div>
					{f'<div class="party-info"><div class="party-name">{origin_party_name}</div>' + (f'<div class="party-address">{origin_party_address}</div>' if origin_party_address else '') + '</div>' if origin_party_name else ''}
				</div>
				<div class="header-column">
					<div class="header-section">
						<label class="section-label">DESTINATION</label>
						<div class="location-name">{destination_name or "Destination"}</div>
					</div>
					{f'<div class="party-info"><div class="party-name">{destination_party_name}</div>' + (f'<div class="party-address">{destination_party_address}</div>' if destination_party_address else '') + '</div>' if destination_party_name else ''}
				</div>
			</div>
			{f'<div class="header-details">{detail_html}</div>' if detail_html else ''}
		</div>
		<div class="milestone-container">
			<div class="milestone-cards">
				<div class="milestone-list">
	"""

	for milestone in milestones:
		milestone_info = milestone_details.get(milestone.get("milestone"), {})
		status = milestone.get("status") or "Planned"
		status_class = status.lower().replace(" ", "-")

		# Check if delayed
		planned_end = milestone.get("planned_end")
		actual_end = milestone.get("actual_end")
		if planned_end:
			planned_dt = frappe.utils.get_datetime(planned_end)
			now = frappe.utils.now_datetime()
			if (not actual_end and planned_dt < now) or (actual_end and frappe.utils.get_datetime(actual_end) > planned_dt):
				if not actual_end or frappe.utils.get_datetime(actual_end) <= planned_dt:
					status = "Delayed"
					status_class = "delayed"

		original_status = milestone.get("status") or "Planned"
		if actual_end and planned_end and frappe.utils.get_datetime(actual_end) > frappe.utils.get_datetime(planned_end) and original_status.lower() in ["completed", "finished", "done"]:
			status_badges = '<span class="status-badge completed">Completed</span><span class="status-badge delayed">Delayed</span>'
		else:
			status_badges = f'<span class="status-badge {status_class}">{status}</span>'

		action_icons = []
		if not milestone.get("actual_start"):
			action_icons.append(
				f'<i class="fa fa-play-circle action-icon start-icon" title="Capture Actual Start" '
				f'onclick="captureActualStart(\'{milestone.get("name")}\')" style="color: #28a745; cursor: pointer;"></i>'
			)
		if not milestone.get("actual_end"):
			action_icons.append(
				f'<i class="fa fa-stop-circle action-icon end-icon" title="Capture Actual End" '
				f'onclick="captureActualEnd(\'{milestone.get("name")}\')" style="color: #dc3545; cursor: pointer;"></i>'
			)
		action_icons.append(
			f'<i class="fa fa-eye action-icon view-icon" title="View Milestone" '
			f'onclick="viewMilestone(\'{milestone.get("name")}\')" style="color: #007bff; cursor: pointer;"></i>'
		)

		html += f"""
						<div class="milestone-card {status_class}">
							<div class="milestone-header">
								<h5>{milestone_info.get("description", milestone.get("milestone") or "Unknown")}</h5>
								<div class="milestone-actions">
									<div class="status-badges">{status_badges}</div>
									<div class="action-icons">{''.join(action_icons)}</div>
								</div>
							</div>
							<div class="milestone-dates">
								<div class="date-row"><label>Planned:</label><span>{format_datetime_fn(planned_end) or "Not set"}</span></div>
								<div class="date-row"><label>Actual:</label><span>{format_datetime_fn(actual_end) or "Not completed"}</span></div>
							</div>
						</div>
		"""

	html += """
				</div>
			</div>
		</div>
		<style>
		.job-header { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 20px; padding: 12px 16px; }
		.header-main { display: flex; justify-content: space-between; padding-bottom: 10px; border-bottom: 1px solid #e0e0e0; gap: 40px; }
		.header-column { flex: 1; display: flex; flex-direction: column; gap: 5px; }
		.section-label { font-size: 10px; color: #6c757d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
		.location-name { font-size: 16px; font-weight: 600; color: #007bff; }
		.party-name { font-size: 13px; font-weight: 500; color: #333; }
		.party-address { font-size: 11px; color: #666; margin-top: 2px; }
		.header-details { display: flex; gap: 20px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f0f0f0; }
		.detail-item label { font-size: 10px; color: #6c757d; font-weight: 600; }
		.detail-item span { font-size: 12px; color: #333; }
		.milestone-container { display: flex; flex-direction: column; gap: 20px; }
		.milestone-cards { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; }
		.milestone-list { display: flex; flex-direction: column; gap: 12px; }
		.milestone-card { background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px; padding: 12px; }
		.milestone-card.completed { border-left: 4px solid #28a745; }
		.milestone-card.delayed { border-left: 4px solid #dc3545; }
		.milestone-card.planned { border-left: 4px solid #6c757d; }
		.milestone-card.started { border-left: 4px solid #007bff; }
		.milestone-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
		.milestone-header h5 { margin: 0; font-size: 14px; font-weight: 600; color: #333; }
		.milestone-actions { display: flex; gap: 8px; align-items: center; }
		.status-badge { padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 600; text-transform: uppercase; }
		.status-badge.completed { background: #d4edda; color: #155724; }
		.status-badge.delayed { background: #f8d7da; color: #721c24; }
		.status-badge.planned { background: #e2e3e5; color: #383d41; }
		.status-badge.started { background: #cce5ff; color: #004085; }
		.action-icons { display: flex; gap: 8px; }
		.action-icon { font-size: 16px; cursor: pointer; }
		.milestone-dates { display: flex; flex-direction: column; gap: 4px; }
		.date-row { display: flex; justify-content: space-between; align-items: center; }
		.date-row label { font-size: 11px; color: #6c757d; font-weight: 600; }
		.date-row span { font-size: 12px; color: #333; }
		</style>
		<script>
		function captureActualStart(milestoneId) {
			frappe.prompt([{fieldname: 'actual_start', fieldtype: 'Datetime', label: 'Actual Start', reqd: 1, default: frappe.datetime.now_datetime()}], function(values) {
				frappe.call({method: 'frappe.client.set_value', args: {doctype: 'Job Milestone', name: milestoneId, fieldname: 'actual_start', value: values.actual_start}}, function() {
					frappe.ui.form.get_cur_frm().call('get_milestone_html').then(function(r) { if (r.message) frappe.ui.form.get_cur_frm().get_field('milestone_html').$wrapper.html(r.message); });
				});
			});
		}
		function captureActualEnd(milestoneId) {
			frappe.prompt([{fieldname: 'actual_end', fieldtype: 'Datetime', label: 'Actual End', reqd: 1, default: frappe.datetime.now_datetime()}], function(values) {
				frappe.call({method: 'frappe.client.set_value', args: {doctype: 'Job Milestone', name: milestoneId, fieldname: 'actual_end', value: values.actual_end}}, function() {
					frappe.ui.form.get_cur_frm().call('get_milestone_html').then(function(r) { if (r.message) frappe.ui.form.get_cur_frm().get_field('milestone_html').$wrapper.html(r.message); });
				});
			});
		}
		function viewMilestone(milestoneId) { frappe.set_route('Form', 'Job Milestone', milestoneId); }
		</script>
	"""

	return (doc_alerts + html) if doc_alerts else html
