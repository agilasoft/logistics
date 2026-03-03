# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared milestone HTML builder for Jobs, Shipments, and Declarations."""

from __future__ import unicode_literals

import json
import frappe


def _get_milestone_attr(m, key, default=None):
	"""Get attribute from milestone (dict or object)."""
	if isinstance(m, dict):
		return m.get(key, default)
	return getattr(m, key, default)


def _render_icon_html(icon):
	"""Render icon as HTML using Frappe/Lucide SVG icons (same as Logistics Milestone Icon field)."""
	if not icon or not str(icon).strip():
		icon = "circle"
	icon = str(icon).strip()
	# Normalize: spaces to hyphens, lowercase for symbol id
	safe_name = icon.replace(" ", "-").replace("_", "-").lower()
	if not safe_name:
		safe_name = "circle"
	# Frappe Icon field uses Lucide symbols: #icon-{name}
	symbol_id = "icon-" + frappe.utils.escape_html(safe_name)
	return f'<svg class="icon icon-sm" aria-hidden="true"><use href="#{symbol_id}"></use></svg>'


def _compute_milestone_status(m):
	"""Return (display_status, is_delayed) for a milestone."""
	status = (_get_milestone_attr(m, "status") or "Planned").strip()
	planned_end = _get_milestone_attr(m, "planned_end")
	actual_end = _get_milestone_attr(m, "actual_end")
	actual_start = _get_milestone_attr(m, "actual_start")
	now = frappe.utils.now_datetime()

	is_delayed = False
	if planned_end:
		planned_dt = frappe.utils.get_datetime(planned_end)
		if not actual_end:
			if planned_dt < now:
				is_delayed = True
				status = "Delayed"
		else:
			actual_dt = frappe.utils.get_datetime(actual_end)
			if actual_dt > planned_dt:
				is_delayed = True
				if status.lower() not in ("completed", "finished", "done"):
					status = "Delayed"

	# Normalize status for counting
	if status.lower() in ("completed", "finished", "done"):
		return "completed", is_delayed
	if status.lower() in ("delayed", "overdue"):
		return "delayed", True
	if status.lower() in ("started", "in progress", "in_progress") or (actual_start and not actual_end):
		return "started", is_delayed
	return "planned", is_delayed


def build_milestone_table_html(doctype, docname, job_type, format_datetime_fn):
	"""
	Build a virtual table HTML showing all Job Milestones for the given job.
	Includes: graphical timeline with dots, number cards (Total, Completed, In Progress, Planned, Exceptions), table.
	"""
	if not docname or docname == "new":
		return '<div class="alert alert-info">Save the document to view milestones.</div>'

	milestones = frappe.get_all(
		"Job Milestone",
		filters={"job_type": job_type, "job_number": docname},
		fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
		order_by="planned_start",
	)

	milestone_details = {}
	if milestones:
		names = [m.milestone for m in milestones if m.milestone]
		if names:
			for lm in frappe.get_all(
				"Logistics Milestone",
				filters={"name": ["in", names]},
				fields=["name", "description"],
			):
				milestone_details[lm.name] = lm.description or lm.name

	# Compute counts and per-milestone status for timeline
	count_total = len(milestones)
	count_completed = 0
	count_started = 0
	count_planned = 0
	count_exceptions = 0
	timeline_dots = []

	for m in milestones:
		display_status, is_delayed = _compute_milestone_status(m)
		if display_status == "completed":
			count_completed += 1
		elif display_status == "started":
			count_started += 1
		else:
			count_planned += 1
		if is_delayed:
			count_exceptions += 1
		timeline_dots.append({"status": display_status, "is_delayed": is_delayed})

	# Build timeline HTML (horizontal line from first to last, smaller colored dots)
	timeline_html = ""
	if milestones:
		n = len(milestones)
		dots_html = []
		for i, dot in enumerate(timeline_dots):
			bg = "#28a745" if dot["status"] == "completed" else "#007bff" if dot["status"] == "started" else "#dc3545" if dot["is_delayed"] else "#6c757d"
			title = milestone_details.get(milestones[i].milestone, milestones[i].milestone or "—")
			pct = 100.0 * (i + 0.5) / n if n > 1 else 50
			dots_html.append(
				'<div title="%s" style="position:absolute;top:50%%;left:%s%%;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%%;background:%s;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,0.2);"></div>'
				% (frappe.utils.escape_html(title), pct, bg)
			)
		# Line segments: each segment from dot i to dot i+1, colored by next dot
		line_segments = []
		for i in range(n - 1):
			left_pct = 100.0 * (i + 0.5) / n
			right_pct = 100.0 * (i + 1.5) / n
			seg_bg = "#28a745" if timeline_dots[i + 1]["status"] == "completed" else "#007bff" if timeline_dots[i + 1]["status"] == "started" else "#dc3545" if timeline_dots[i + 1]["is_delayed"] else "#6c757d"
			line_segments.append(
				'<div style="position:absolute;top:50%%;left:%s%%;width:%s%%;height:3px;margin-top:-2px;background:%s;border-radius:2px;"></div>'
				% (left_pct, right_pct - left_pct, seg_bg)
			)
		line_html = "".join(line_segments) if line_segments else ""
		timeline_html = (
			'<div style="position:relative;height:28px;margin:0 0 16px 0;width:100%%;">'
			+ line_html +
			"".join(dots_html) +
			'</div>'
		)

	# Number cards - Frappe widget style (widget number-widget-box)
	def _card(label, value, number_style="", card_style=""):
		return (
			'<div class="widget number-widget-box" style="min-width:100px;flex:1;%s">'
			'<div class="widget-head"><div class="widget-label"><div class="widget-title">%s</div></div></div>'
			'<div class="widget-body"><div class="widget-content"><div class="number" style="%s">%d</div></div></div>'
			'</div>'
		) % (card_style, frappe.utils.escape_html(label), number_style, value)

	cards_container = (
		'<div class="d-flex flex-wrap" style="margin-bottom:16px;gap:12px;">'
		+ _card("Total", count_total, "color: var(--text-color)")
		+ _card("Completed", count_completed, "color: var(--green-500)")
		+ _card("In Progress", count_started, "color: var(--blue-500)")
		+ _card("Planned", count_planned, "color: var(--gray-600)")
		+ _card("Exceptions", count_exceptions, "color: var(--red-500)", "border-color: var(--red-500); background: var(--red-50);")
		+ '</div>'
	)
	cards_html = cards_container

	rows = []
	for m in milestones:
		desc = milestone_details.get(m.milestone, m.milestone or "—")
		display_status, is_delayed = _compute_milestone_status(m)
		status_label = "Delayed" if (display_status == "delayed" or is_delayed) else (m.status or "Planned").strip()
		status_class = "label-success" if display_status == "completed" else "label-info" if display_status == "started" else "label-danger" if display_status == "delayed" or is_delayed else "label-default"
		planned_start = format_datetime_fn(m.planned_start) if m.planned_start else "—"
		planned_end = format_datetime_fn(m.planned_end) if m.planned_end else "—"
		actual_start = format_datetime_fn(m.actual_start) if m.actual_start else "—"
		actual_end = format_datetime_fn(m.actual_end) if m.actual_end else "—"
		open_link = '<a href="#Form/Job Milestone/%s" class="btn btn-xs btn-default">Open</a>' % (
			frappe.utils.escape_html(m.name) if m.name else ""
		)
		rows.append(
			"<tr><td>%s</td><td><span class=\"label %s\">%s</span></td>"
			"<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
			% (
				frappe.utils.escape_html(desc),
				status_class,
				frappe.utils.escape_html(status_label),
				frappe.utils.escape_html(planned_start),
				frappe.utils.escape_html(planned_end),
				frappe.utils.escape_html(actual_start),
				frappe.utils.escape_html(actual_end),
				open_link,
			)
		)

	table_body = "\n".join(rows) if rows else '<tr><td colspan="7" class="text-muted text-center">No milestones found.</td></tr>'

	html = """
	<div style="margin:0;">
		%s
		%s
		<div style="margin:16px 0 0 0;">
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<th>Milestone</th>
						<th>Status</th>
						<th>Planned Start</th>
						<th>Planned End</th>
						<th>Actual Start</th>
						<th>Actual End</th>
						<th style="width: 80px;">Actions</th>
					</tr>
				</thead>
				<tbody>
					%s
				</tbody>
			</table>
		</div>
	</div>
	""" % (
		timeline_html,
		cards_html,
		table_body,
	)
	return html


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
	include_doc_alerts=True,
	include_origin_destination=True,
	child_milestone_doctype=None,
	refresh_method=None,
	refresh_arg_name=None,
):
	"""
	Build milestone HTML for Milestones tab.
	detail_items: list of (label, value) for header details.
	include_doc_alerts: if False, omit document alerts (use when Dashboard tab shows them separately).
	include_origin_destination: if False, omit ORIGIN/DESTINATION header (shown in Dashboard tab instead).
	"""
	doc_alerts = ""
	if include_doc_alerts:
		from logistics.document_management.api import get_document_alerts_html
		doc_alerts = get_document_alerts_html(doctype, docname or "new")

	# Get milestone details (including icon from master)
	milestone_details = {}
	if milestones:
		milestone_names = [m.get("milestone") for m in milestones if m.get("milestone")]
		if milestone_names:
			milestone_data = frappe.get_all(
				"Logistics Milestone",
				filters={"name": ["in", milestone_names]},
				fields=["name", "description", "code", "icon"],
			)
			milestone_details = {m.name: m for m in milestone_data}

	# Build header
	detail_html = ""
	for label, value in (detail_items or []):
		if value:
			detail_html += f'<div class="detail-item"><label>{label}:</label><span>{value}</span></div>'

	# Origin/Destination section (omit when shown in Dashboard tab)
	origin_dest_section = ""
	if include_origin_destination:
		origin_dest_section = f"""
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
		</div>"""
	elif detail_html:
		origin_dest_section = f'<div class="job-header"><div class="header-details">{detail_html}</div></div>'

	html = f"""
		{origin_dest_section}
		<div class="milestone-container">
			<div class="milestone-cards">
	"""

	# Build graphical timeline with dots (colored circles, no icon inside) + labels with icons
	timeline_html = ""
	if milestones:
		timeline_dots = []
		for i, m in enumerate(milestones):
			display_status, is_delayed = _compute_milestone_status(m)
			info = milestone_details.get(m.get("milestone"), {})
			desc = info.get("description") or m.get("milestone") or "—"
			icon = info.get("icon") or "circle"
			if not icon or str(icon).strip() == "":
				icon = "circle"
			icon_html = _render_icon_html(icon)
			bg = "#28a745" if display_status == "completed" else "#007bff" if display_status == "started" else "#dc3545" if is_delayed else "#6c757d"
			pct = 100.0 * (i + 0.5) / len(milestones) if len(milestones) > 1 else 50
			timeline_dots.append({
				"pct": pct, "bg": bg, "icon_html": icon_html, "desc": desc, "title": frappe.utils.escape_html(desc),
			})
		# Dots: colored circles only (no icon inside)
		dots_html = "".join(
			'<div class="milestone-timeline-dot" title="%(title)s" style="left:%(pct)s%%;background:%(bg)s"></div>' % d
			for d in timeline_dots
		)
		# Line segments: each segment from dot i to dot i+1, colored by next dot
		n = len(timeline_dots)
		line_segments = []
		for i in range(n - 1):
			left_pct = timeline_dots[i]["pct"]
			right_pct = timeline_dots[i + 1]["pct"]
			seg_color = timeline_dots[i + 1]["bg"]
			line_segments.append(
				'<div class="milestone-timeline-line" style="left:%s%%;width:%s%%;background:%s"></div>'
				% (left_pct, right_pct - left_pct, seg_color)
			)
		line_html = "".join(line_segments) if line_segments else ""
		timeline_html = (
			'<div class="milestone-timeline">'
			+ line_html +
			dots_html +
			'</div>'
			'<div class="milestone-timeline-labels">'
			+ "".join(
				'<div class="milestone-timeline-label" style="left:%s%%" title="%s">'
				'<div class="milestone-label-icon">%s</div>'
				'<span class="milestone-label-desc">%s</span>'
				'</div>'
				% (d["pct"], d["title"], d["icon_html"], frappe.utils.escape_html(d["desc"][:30] + ("…" if len(d["desc"]) > 30 else "")))
				for d in timeline_dots
			) +
			'</div>'
		)

	html += timeline_html

	html += """
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
		.milestone-container { display: flex; flex-direction: column; gap: 20px; margin-bottom: 24px; }
		.milestone-cards { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 16px; }
		.milestone-timeline { position: relative; height: 40px; margin-bottom: 8px; }
		.milestone-timeline-line { position: absolute; top: 50%; height: 3px; margin-top: -2px; background: #dee2e6; border-radius: 2px; }
		.milestone-timeline-dot { position: absolute; top: 50%; width: 14px; height: 14px; margin-left: -7px; margin-top: -7px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }
		.milestone-timeline-labels { position: relative; height: 56px; margin-bottom: 12px; }
		.milestone-timeline-label { position: absolute; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; max-width: 80px; text-align: center; }
		.milestone-label-icon { margin-bottom: 4px; color: #6c757d; }
		.milestone-label-icon svg { width: 18px; height: 18px; stroke: currentColor; }
		.milestone-label-desc { font-size: 10px; color: #6c757d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; }
		@media (max-width: 768px) {
			.milestone-label-desc { display: none; }
			.milestone-timeline-labels { height: 32px; }
		}
		</style>
		<script>
		var _milestoneChildDoctype = """ + json.dumps(child_milestone_doctype or "Job Milestone") + """;
		var _milestoneRefreshMethod = """ + json.dumps(refresh_method or "logistics.document_management.api.get_milestone_html") + """;
		var _milestoneRefreshArgName = """ + json.dumps(refresh_arg_name or "docname") + """;
		function _refreshMilestoneHtml() {
			var frm = frappe.ui.form.get_cur_frm();
			if (!frm || !frm.doc.name || frm.doc.__islocal) return;
			var args = _milestoneRefreshArgName === 'special_project'
				? { special_project: frm.doc.name }
				: { doctype: frm.doctype, docname: frm.doc.name };
			frappe.call({
				method: _milestoneRefreshMethod,
				args: args,
				callback: function(r) {
					if (r.message && frm.fields_dict.milestone_html) {
						frm.fields_dict.milestone_html.$wrapper.html(r.message);
					}
				}
			});
		}
		function captureActualStart(milestoneDoctype, milestoneId) {
			var dt = milestoneDoctype || _milestoneChildDoctype;
			frappe.prompt([{fieldname: 'actual_start', fieldtype: 'Datetime', label: 'Actual Start', reqd: 1, default: frappe.datetime.now_datetime()}], function(values) {
				frappe.call({
					method: 'frappe.client.set_value',
					args: { doctype: dt, name: milestoneId, fieldname: 'actual_start', value: values.actual_start }
				}, function() { _refreshMilestoneHtml(); });
			});
		}
		function captureActualEnd(milestoneDoctype, milestoneId) {
			var dt = milestoneDoctype || _milestoneChildDoctype;
			frappe.prompt([{fieldname: 'actual_end', fieldtype: 'Datetime', label: 'Actual End', reqd: 1, default: frappe.datetime.now_datetime()}], function(values) {
				frappe.call({
					method: 'frappe.client.set_value',
					args: { doctype: dt, name: milestoneId, fieldname: 'actual_end', value: values.actual_end }
				}, function() { _refreshMilestoneHtml(); });
			});
		}
		</script>
	"""

	return (doc_alerts + html) if doc_alerts else html
