// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Consolidation", {
	refresh(frm) {
		// Add custom button to fetch consolidatable jobs
		frm.add_custom_button(__("Jobs"), function() {
			fetch_consolidatable_jobs(frm);
		}, __("Fetch"));
		
		// Add custom button to create Run Sheet
		if (!frm.doc.__islocal && frm.doc.transport_jobs && frm.doc.transport_jobs.length > 0) {
			frm.add_custom_button(__("Run Sheet"), function() {
				create_run_sheet_from_consolidation(frm);
			}, __("Create"));
		}
	},
});

function fetch_consolidatable_jobs(frm) {
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.get_consolidatable_jobs",
		args: {
			consolidation_type: frm.doc.consolidation_type || null,
			company: frm.doc.company || null,
			date: frm.doc.consolidation_date || null
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				show_jobs_dialog(frm, r.message.jobs, r.message.consolidation_groups);
			} else {
				frappe.show_alert({
					message: __("Error fetching jobs: {0}", [r.message.message || "Unknown error"]),
					indicator: "red"
				});
			}
		},
		error: function(r) {
			frappe.show_alert({
				message: __("Error fetching jobs"),
				indicator: "red"
			});
		}
	});
}

function show_jobs_dialog(frm, jobs, consolidation_groups) {
	if (!jobs || jobs.length === 0) {
		frappe.msgprint({
			title: __("No Jobs Found"),
			message: __("No consolidatable jobs found matching the criteria."),
			indicator: "orange"
		});
		return;
	}
	
	let selected_jobs = [];
	
	const dialog = new frappe.ui.Dialog({
		title: __("Consolidatable Jobs"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<div style="margin-bottom: 15px;">
					<p style="font-size: 13px; color: #6c757d;">
						Found <strong>${jobs.length}</strong> job(s) that can be consolidated.
						${consolidation_groups && consolidation_groups.length > 0 ? 
							`<br>Grouped into <strong>${consolidation_groups.length}</strong> consolidation group(s).` : ''}
					</p>
				</div>`
			},
			{
				fieldtype: "Section Break",
				label: __("Available Jobs")
			},
			{
				fieldname: "jobs_table",
				fieldtype: "HTML",
				options: build_jobs_table_html(jobs, consolidation_groups)
			},
			{
				fieldtype: "Section Break"
			},
			{
				fieldname: "select_all",
				fieldtype: "Check",
				label: __("Select All"),
				default: 0
			}
		],
		primary_action_label: __("Add Selected Jobs"),
		primary_action: function(values) {
			// Get selected jobs from checkboxes
			const checkboxes = dialog.$wrapper.find('.job-checkbox:checked');
			selected_jobs = [];
			checkboxes.each(function() {
				selected_jobs.push($(this).data('job-name'));
			});
			
			if (selected_jobs.length === 0) {
				frappe.msgprint({
					title: __("No Selection"),
					message: __("Please select at least one job to add."),
					indicator: "orange"
				});
				return;
			}
			
			add_jobs_to_consolidation(frm, selected_jobs, dialog);
		}
	});
	
	dialog.show();
	
	// Wait for dialog to render, then set up event handlers
	setTimeout(function() {
		// Handle select all checkbox
		if (dialog.fields_dict.select_all) {
			dialog.fields_dict.select_all.$input.on('change', function() {
				const checked = $(this).is(':checked');
				dialog.$wrapper.find('.job-checkbox').prop('checked', checked);
			});
		}
		
		// Handle individual checkboxes
		dialog.$wrapper.on('change', '.job-checkbox', function() {
			update_select_all_state();
		});
		
		function update_select_all_state() {
			const total = dialog.$wrapper.find('.job-checkbox').length;
			const checked = dialog.$wrapper.find('.job-checkbox:checked').length;
			if (dialog.fields_dict.select_all) {
				dialog.fields_dict.select_all.set_value(checked === total && total > 0);
			}
		}
	}, 100);
}

function build_jobs_table_html(jobs, consolidation_groups) {
	let html = `
		<div style="max-height: 400px; overflow-y: auto; border: 1px solid #d1d5db; border-radius: 4px;">
			<table class="table table-bordered table-condensed" style="font-size: 12px; margin: 0;">
				<thead>
					<tr style="background-color: #f8f9fa;">
						<th style="width: 30px; text-align: center; padding: 8px;">
							<input type="checkbox" class="select-all-checkbox">
						</th>
						<th style="padding: 8px;">${__("Job")}</th>
						<th style="padding: 8px;">${__("Customer")}</th>
						<th style="padding: 8px;">${__("Pick Address")}</th>
						<th style="padding: 8px;">${__("Drop Address")}</th>
						<th style="padding: 8px;">${__("Type")}</th>
						<th style="padding: 8px;">${__("Status")}</th>
					</tr>
				</thead>
				<tbody>
	`;
	
	jobs.forEach(function(job) {
		const consolidation_badge = job.consolidation_type === 'Pick Consolidated' ? 
			'<span class="badge badge-info" style="background-color: #007bff;">Pick</span>' : 
			(job.consolidation_type === 'Drop Consolidated' ? 
				'<span class="badge badge-success" style="background-color: #28a745;">Drop</span>' : '-');
		
		const status_badge_color = get_status_color(job.status);
		
		html += `
			<tr>
				<td style="text-align: center; padding: 8px;">
					<input type="checkbox" class="job-checkbox" data-job-name="${job.name}">
				</td>
				<td style="padding: 8px;">
					<a href="/app/transport-job/${job.name}" target="_blank">${job.name}</a>
				</td>
				<td style="padding: 8px;">${job.customer || '-'}</td>
				<td style="padding: 8px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${job.pick_address || '-'}">${job.pick_address || '-'}</td>
				<td style="padding: 8px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${job.drop_address || '-'}">${job.drop_address || '-'}</td>
				<td style="padding: 8px;">${consolidation_badge}</td>
				<td style="padding: 8px;">
					<span class="badge badge-${status_badge_color}">${job.status || 'Draft'}</span>
				</td>
			</tr>
		`;
	});
	
	html += `
				</tbody>
			</table>
		</div>
	`;
	
	return html;
}

function get_status_color(status) {
	const statusColors = {
		'Draft': 'secondary',
		'Submitted': 'primary',
		'In Progress': 'info',
		'Completed': 'success',
		'Cancelled': 'danger'
	};
	return statusColors[status] || 'secondary';
}

function add_jobs_to_consolidation(frm, job_names, dialog) {
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.add_jobs_to_consolidation",
		args: {
			consolidation_name: frm.doc.name,
			job_names: job_names
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				frappe.show_alert({
					message: __("Added {0} job(s) to consolidation", [r.message.added_count]),
					indicator: "green"
				});
				dialog.hide();
				frm.reload_doc();
			} else {
				frappe.show_alert({
					message: __("Error adding jobs: {0}", [r.message.message || "Unknown error"]),
					indicator: "red"
				});
			}
		},
		error: function(r) {
			frappe.show_alert({
				message: __("Error adding jobs"),
				indicator: "red"
			});
		}
	});
}

function create_run_sheet_from_consolidation(frm) {
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.create_run_sheet_from_consolidation",
		args: {
			consolidation_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				frappe.show_alert({
					message: __("Run Sheet {0} created successfully", [r.message.run_sheet_name]),
					indicator: "green"
				});
				// Reload the form to show the linked Run Sheet
				frm.reload_doc();
				// Open the created Run Sheet
				if (r.message.run_sheet_name) {
					frappe.set_route("Form", "Run Sheet", r.message.run_sheet_name);
				}
			} else {
				frappe.show_alert({
					message: __("Error creating Run Sheet: {0}", [r.message.message || "Unknown error"]),
					indicator: "red"
				});
			}
		},
		error: function(r) {
			frappe.show_alert({
				message: __("Error creating Run Sheet"),
				indicator: "red"
			});
		}
	});
}
