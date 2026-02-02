// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Consolidation", {
	refresh(frm) {
		// Add custom button to fetch jobs (always show dialog for manual selection)
		frm.add_custom_button(__("Jobs"), function() {
			fetch_consolidatable_jobs(frm);
		}, __("Fetch"));
		
		// Add custom button to create Run Sheet
		if (!frm.doc.__islocal && frm.doc.transport_jobs && frm.doc.transport_jobs.length > 0) {
			frm.add_custom_button(__("Run Sheet"), function() {
				create_run_sheet_from_consolidation(frm);
			}, __("Create"));
		}
		
		// Set query filter for transport_job field in child table
		// Exclude jobs that have any leg with run_sheet assigned
		frm.set_query("transport_job", "transport_jobs", function() {
			// Call server method to get filters
			let filters = { docstatus: 1 }; // Default: only submitted jobs
			
			frappe.call({
				method: "logistics.transport.doctype.transport_consolidation_job.transport_consolidation_job.get_transport_job_filter",
				async: false,
				callback: function(r) {
					if (r.message) {
						filters = r.message;
					}
				}
			});
			
			return {
				filters: filters
			};
		});
	},
	
	consolidation_type(frm) {
		// When consolidation_type changes in the form, update the dialog if it's open
		if (frm._consolidation_dialog && frm._consolidation_dialog.fields_dict && 
		    frm._consolidation_dialog.fields_dict.filter_consolidation_type) {
			const current_dialog_value = frm._consolidation_dialog.fields_dict.filter_consolidation_type.get_value() || "";
			const form_value = frm.doc.consolidation_type || "";
			if (current_dialog_value !== form_value) {
				// Prevent recursive update
				if (frm._consolidation_dialog._updating_from_dialog) {
					return;
				}
				const field = frm._consolidation_dialog.fields_dict.filter_consolidation_type;
				field.set_value(form_value);
				// Trigger filter update if filter_jobs function is available
				if (frm._consolidation_dialog._filter_jobs) {
					setTimeout(function() {
						frm._consolidation_dialog._filter_jobs();
					}, 100);
				}
			}
		}
	}
});

// Handle child table events for Transport Consolidation Job
frappe.ui.form.on("Transport Consolidation Job", {
	transport_job(frm, cdt, cdn) {
		// When transport_job is selected, calculate weight and volume from packages
		let row = locals[cdt][cdn];
		if (row.transport_job) {
			// Call server method to calculate weight and volume
			frappe.call({
				method: "logistics.transport.doctype.transport_consolidation_job.transport_consolidation_job.calculate_weight_volume_from_job",
				args: {
					transport_job: row.transport_job,
					company: frm.doc.company || null
				},
				callback: function(r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "weight", r.message.weight || 0);
						frappe.model.set_value(cdt, cdn, "volume", r.message.volume || 0);
					}
				}
			});
		} else {
			// Clear weight and volume if transport_job is cleared
			frappe.model.set_value(cdt, cdn, "weight", 0);
			frappe.model.set_value(cdt, cdn, "volume", 0);
		}
	}
});

function fetch_matching_jobs(frm) {
	// Check if document is saved before fetching jobs
	if (frm.doc.__islocal) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Transport Consolidation first before fetching matching jobs."),
			indicator: "orange"
		});
		return;
	}
	
	// Automatically find and add matching jobs
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.fetch_matching_jobs",
		args: {
			consolidation_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				frappe.show_alert({
					message: __("Added {0} matching job(s) to consolidation", [r.message.added_count || 0]),
					indicator: "green"
				});
				frm.reload_doc();
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

function fetch_consolidatable_jobs(frm) {
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.get_consolidatable_jobs",
		args: {
			consolidation_type: frm.doc.consolidation_type || null,
			company: frm.doc.company || null,
			date: frm.doc.consolidation_date || null,
			current_consolidation: frm.doc.name && !frm.doc.__islocal ? frm.doc.name : null
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				show_jobs_dialog(frm, r.message.jobs, r.message.consolidation_groups, r.message.debug);
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

function fetch_legs_for_jobs(job_names, callback) {
	// Fetch transport legs for the given job names
	if (!job_names || job_names.length === 0) {
		callback([]);
		return;
	}
	
	// Get unique job names
	const unique_job_names = [...new Set(job_names)];
	
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.get_consolidatable_legs",
		args: {
			job_names: unique_job_names
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				callback(r.message.legs || []);
			} else {
				callback([]);
			}
		},
		error: function() {
			callback([]);
		}
	});
}

function reload_jobs_with_filter(frm, dialog, consolidation_type) {
	// Show loading indicator
	if (dialog.fields_dict.summary_info) {
		dialog.fields_dict.summary_info.$wrapper.html('<div style="padding: 20px; text-align: center;"><i class="fa fa-spinner fa-spin"></i> ' + __("Loading jobs...") + '</div>');
	}
	
	// Clear legs cache when jobs are reloaded
	if (dialog._jobs_data) {
		dialog._jobs_data.all_legs = [];
		dialog._jobs_data.filtered_legs = [];
	}
	// Also clear legs in dialog scope if they exist
	if (dialog._all_legs) {
		dialog._all_legs = [];
		dialog._filtered_legs = [];
	}
	
	// Re-fetch jobs from server with new consolidation_type filter
	frappe.call({
		method: "logistics.transport.doctype.transport_consolidation.transport_consolidation.get_consolidatable_jobs",
		args: {
			consolidation_type: consolidation_type || null,
			company: frm.doc.company || null,
			date: frm.doc.consolidation_date || null,
			current_consolidation: frm.doc.name && !frm.doc.__islocal ? frm.doc.name : null
		},
		callback: function(r) {
			if (r.message && r.message.status === "success") {
				// Update the jobs list in the dialog
				update_dialog_jobs(dialog, r.message.jobs, r.message.consolidation_groups, r.message.debug);
				// If currently viewing legs, switch back to jobs view
				if (dialog._switch_view && dialog._current_view === "legs") {
					dialog._switch_view("jobs");
				}
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

function setup_diagnostics_toggle(dialog) {
	// Setup toggle functionality for collapsible diagnostics section
	setTimeout(function() {
		dialog.$wrapper.find('.diagnostics-toggle-header').off('click').on('click', function() {
			const $header = $(this);
			const targetId = $header.data('target');
			const $content = $('#' + targetId);
			const $icon = $header.find('.diagnostics-toggle-icon');
			
			if ($content.is(':visible')) {
				$content.slideUp(200);
				$icon.css('transform', 'rotate(0deg)');
			} else {
				$content.slideDown(200);
				$icon.css('transform', 'rotate(180deg)');
			}
		});
	}, 100);
}

function setup_filter_toggle(dialog) {
	// Setup toggle functionality for collapsible filter section
	setTimeout(function() {
		const $filterContent = dialog.$wrapper.find('#filter_section_content');
		const $filterHeader = dialog.$wrapper.find('.filter-toggle-header');
		
		if (!$filterContent.length || !$filterHeader.length) {
			return;
		}
		
		// Find and move filter fields into the collapsible container
		const filterFieldNames = ['filter_customer', 'filter_pick_address', 'filter_drop_address', 
			'filter_consolidation_type', 'sort_by', 'sort_order'];
		
		// Find the section containing the filter header
		const $headerSection = $filterHeader.closest('.form-section');
		
		// Find all form sections between header and footer
		let $currentSection = $headerSection.next('.form-section');
		while ($currentSection.length) {
			// Check if we've reached the footer section
			if ($currentSection.find('[data-fieldname="filter_section_footer"]').length) {
				break;
			}
			
			// Move form groups and columns from this section into filter content
			const $formGroups = $currentSection.find('.form-group');
			const $formColumns = $currentSection.find('.form-column');
			
			if ($formGroups.length || $formColumns.length) {
				$formGroups.appendTo($filterContent);
				$formColumns.appendTo($filterContent);
			}
			
			$currentSection = $currentSection.next('.form-section');
		}
		
		// Also ensure all filter fields are in the content (fallback)
		filterFieldNames.forEach(function(fieldname) {
			const $fieldWrapper = dialog.$wrapper.find(`[data-fieldname="${fieldname}"]`).closest('.form-group');
			if ($fieldWrapper.length && !$filterContent.find($fieldWrapper).length) {
				$fieldWrapper.appendTo($filterContent);
			}
		});
		
		// Setup toggle click handler
		$filterHeader.off('click').on('click', function() {
			const $header = $(this);
			const targetId = $header.data('target');
			const $content = $('#' + targetId);
			const $icon = $header.find('.filter-toggle-icon');
			
			if ($content.is(':visible')) {
				$content.slideUp(200);
				$icon.css('transform', 'rotate(0deg)');
			} else {
				$content.slideDown(200);
				$icon.css('transform', 'rotate(180deg)');
			}
		});
	}, 300);
}

function setup_address_tooltips(dialog) {
	// Setup tooltip positioning for Route consolidation addresses
	setTimeout(function() {
		const $container = dialog.fields_dict.jobs_table.$wrapper.find('.address-tooltip-container');
		const wrappers = dialog.fields_dict.jobs_table.$wrapper.find('.address-tooltip-wrapper');
		
		// Function to update tooltip position
		function updateTooltipPosition($wrapper, $tooltip, $addressText) {
			if ($tooltip.is(':visible') || $tooltip.css('visibility') === 'visible') {
				const rect = $addressText[0].getBoundingClientRect();
				$tooltip.css({
					position: 'fixed',
					left: rect.left + 'px',
					bottom: (window.innerHeight - rect.top + 8) + 'px',
					zIndex: 10000
				});
			}
		}
		
		wrappers.each(function() {
			const $wrapper = $(this);
			const $tooltip = $wrapper.find('.address-tooltip');
			if ($tooltip.length === 0) return;
			
			const $addressText = $wrapper.find('div').first();
			
			// Remove existing handlers to avoid duplicates
			$wrapper.off('mouseenter mouseleave');
			
			$wrapper.on('mouseenter', function() {
				const rect = $addressText[0].getBoundingClientRect();
				$tooltip.css({
					position: 'fixed',
					left: rect.left + 'px',
					bottom: (window.innerHeight - rect.top + 8) + 'px',
					zIndex: 10000
				});
			});
			
			// Update tooltip position on scroll
			$container.off('scroll.tooltip').on('scroll.tooltip', function() {
				updateTooltipPosition($wrapper, $tooltip, $addressText);
			});
		});
	}, 100);
}

function update_dialog_jobs(dialog, jobs, consolidation_groups, debug_info) {
	// Update the jobs data using the dialog's update function if available
	if (dialog._update_jobs_data) {
		dialog._update_jobs_data(jobs, consolidation_groups, debug_info);
	} else {
		// Fallback: update directly
		if (!dialog._jobs_data) {
			dialog._jobs_data = {};
		}
		dialog._jobs_data.all_jobs = jobs || [];
		dialog._jobs_data.filtered_jobs = jobs || [];
		dialog._jobs_data.consolidation_groups = consolidation_groups || [];
		dialog._jobs_data.debug_info = debug_info || {};
	}
	
	// Clear legs cache when jobs are reloaded, so legs will be re-fetched for new job list
	dialog._all_legs = [];
	dialog._filtered_legs = [];
	dialog._legs_job_names = [];
	
	// Update the jobs table
	const table_html = build_jobs_table_html(jobs || [], consolidation_groups || []);
	if (dialog.fields_dict.jobs_table) {
		dialog.fields_dict.jobs_table.$wrapper.html(table_html);
		setup_address_tooltips(dialog);
	}
	
	// Re-apply current filters (if any) to the newly loaded jobs
	if (dialog._filter_jobs) {
		setTimeout(function() {
			dialog._filter_jobs();
		}, 100);
	}
	
	// Update summary info
	if (dialog.fields_dict.summary_info) {
		const has_jobs = jobs && jobs.length > 0;
		
		let diagnostics_html = '';
		if (debug_info) {
			const diagnostics_id = 'diagnostics_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
			let diagnostics_content = '';
			diagnostics_content += __("Total jobs found: {0}", [debug_info.total_jobs_found || 0]) + '<br>';
			diagnostics_content += __("Consolidatable jobs found: {0}", [debug_info.consolidatable_jobs_found || 0]) + '<br>';
			diagnostics_content += __("Consolidation groups found: {0}", [debug_info.consolidation_groups_found || 0]) + '<br>';
			
			if (debug_info.jobs_without_legs > 0) {
				diagnostics_content += __("Jobs without Transport Legs: {0}", [debug_info.jobs_without_legs]) + '<br>';
			}
			if (debug_info.jobs_without_load_type > 0) {
				diagnostics_content += __("Jobs without Load Type: {0}", [debug_info.jobs_without_load_type]) + '<br>';
			}
			if (debug_info.jobs_without_consolidate_flag > 0) {
				diagnostics_content += __("Jobs without consolidate flag set: {0}", [debug_info.jobs_without_consolidate_flag]) + '<br>';
			}
			if (debug_info.jobs_with_invalid_load_type > 0) {
				diagnostics_content += __("Jobs with Load Type that doesn't allow consolidation (can_handle_consolidation=0): {0}", [debug_info.jobs_with_invalid_load_type]) + '<br>';
			}
			if (debug_info.jobs_without_addresses > 0) {
				diagnostics_content += __("Jobs without pick/drop addresses: {0}", [debug_info.jobs_without_addresses]) + '<br>';
			}
			if (debug_info.jobs_already_consolidated > 0) {
				diagnostics_content += __("Jobs already in consolidations: {0}", [debug_info.jobs_already_consolidated]) + '<br>';
			}
			if (debug_info.jobs_with_runsheet > 0) {
				diagnostics_content += __("Jobs with run sheets assigned: {0}", [debug_info.jobs_with_runsheet]) + '<br>';
			}
			if (debug_info.company_filter) {
				diagnostics_content += __("Company filter: {0}", [debug_info.company_filter]) + '<br>';
			}
			if (debug_info.consolidation_type_filter) {
				diagnostics_content += __("Consolidation type filter: {0}", [debug_info.consolidation_type_filter]) + '<br>';
			}
			if (debug_info.current_consolidation) {
				diagnostics_content += __("Current consolidation: {0}", [debug_info.current_consolidation]) + '<br>';
			}
			if (debug_info.message) {
				diagnostics_content += '<br><em>' + debug_info.message + '</em><br>';
			}
			
			diagnostics_html = '<div style="margin-top: 15px; border-radius: 4px; border-left: 3px solid #ffc107; background-color: #f8f9fa;">';
			diagnostics_html += '<div class="diagnostics-toggle-header" data-target="' + diagnostics_id + '" style="padding: 10px; cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between;">';
			diagnostics_html += '<strong>' + __("Diagnostics") + '</strong>';
			diagnostics_html += '<i class="fa fa-chevron-down diagnostics-toggle-icon" style="transition: transform 0.2s;"></i>';
			diagnostics_html += '</div>';
			diagnostics_html += '<div id="' + diagnostics_id + '" class="diagnostics-content" style="display: none; padding: 10px; padding-top: 0;">';
			diagnostics_html += diagnostics_content;
			diagnostics_html += '</div>';
			diagnostics_html += '</div>';
		}
	
	const summary_html = `<div style="margin-bottom: 15px;">
			<p style="font-size: 13px; color: ${has_jobs ? '#6c757d' : '#dc3545'};">
				${has_jobs ? 
					`Found <strong>${jobs.length}</strong> job(s) that can be consolidated.` :
					`<strong>No consolidatable jobs found</strong> matching the criteria.`
				}
				${consolidation_groups && consolidation_groups.length > 0 ? 
					`<br>Grouped into <strong>${consolidation_groups.length}</strong> consolidation group(s).` : 
					(has_jobs ? '<br>No consolidation groups found (jobs may not share common pick/drop addresses).' : '')
				}
			</p>
			${diagnostics_html}
		</div>`;
		dialog.fields_dict.summary_info.$wrapper.html(summary_html);
		
		// Setup toggle functionality for diagnostics
		setup_diagnostics_toggle(dialog);
		
		// Setup toggle functionality for filters
		setup_filter_toggle(dialog);
	}
	
	// Update select all checkbox state
	const total = dialog.$wrapper.find('.job-checkbox').length;
	const checked = dialog.$wrapper.find('.job-checkbox:checked').length;
	const all_checked = checked === total && total > 0;
	if (dialog.fields_dict.select_all) {
		dialog.fields_dict.select_all.set_value(all_checked);
	}
	dialog.$wrapper.find('.select-all-checkbox').prop('checked', all_checked);
	
	// Re-setup event handlers for checkboxes
	dialog.$wrapper.off('change', '.job-checkbox').on('change', '.job-checkbox', function() {
		const total = dialog.$wrapper.find('.job-checkbox').length;
		const checked = dialog.$wrapper.find('.job-checkbox:checked').length;
		const all_checked = checked === total && total > 0;
		if (dialog.fields_dict.select_all) {
			dialog.fields_dict.select_all.set_value(all_checked);
		}
		dialog.$wrapper.find('.select-all-checkbox').prop('checked', all_checked);
	});
}

function show_jobs_dialog(frm, jobs, consolidation_groups, debug_info) {
	// Always show the dialog, even when no jobs are found
	let selected_jobs = [];
	let all_jobs = jobs || []; // Store original jobs list
	let filtered_jobs = jobs || []; // Current filtered list
	let has_jobs = jobs && jobs.length > 0;
	let current_view = "jobs"; // Track current view: "jobs" or "legs"
	
	// Store jobs data in a way that can be accessed by update_dialog_jobs
	// This will be attached to the dialog object later
	
	// Get unique values for filter dropdowns
	const unique_customers = has_jobs ? [...new Set(jobs.map(j => j.customer).filter(Boolean))].sort() : [];
	
	// Collect all unique address IDs from pick_addresses and drop_addresses arrays
	const all_pick_address_ids = new Set();
	const all_drop_address_ids = new Set();
	if (has_jobs) {
		jobs.forEach(function(job) {
			if (job.pick_addresses && Array.isArray(job.pick_addresses)) {
				job.pick_addresses.forEach(function(addr) {
					all_pick_address_ids.add(addr);
				});
			}
			if (job.drop_addresses && Array.isArray(job.drop_addresses)) {
				job.drop_addresses.forEach(function(addr) {
					all_drop_address_ids.add(addr);
				});
			}
		});
	}
	
	
	// Build diagnostics HTML
	let diagnostics_html = '';
	if (debug_info) {
		const diagnostics_id = 'diagnostics_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
		let diagnostics_content = '';
		diagnostics_content += __("Total jobs found: {0}", [debug_info.total_jobs_found || 0]) + '<br>';
		diagnostics_content += __("Consolidatable jobs found: {0}", [debug_info.consolidatable_jobs_found || 0]) + '<br>';
		diagnostics_content += __("Consolidation groups found: {0}", [debug_info.consolidation_groups_found || 0]) + '<br>';
		
		if (debug_info.jobs_without_legs > 0) {
			diagnostics_content += __("Jobs without Transport Legs: {0}", [debug_info.jobs_without_legs]) + '<br>';
		}
		if (debug_info.jobs_without_load_type > 0) {
			diagnostics_content += __("Jobs without Load Type: {0}", [debug_info.jobs_without_load_type]) + '<br>';
		}
		if (debug_info.jobs_without_consolidate_flag > 0) {
			diagnostics_content += __("Jobs without consolidate flag set: {0}", [debug_info.jobs_without_consolidate_flag]) + '<br>';
		}
		if (debug_info.jobs_with_invalid_load_type > 0) {
			diagnostics_content += __("Jobs with Load Type that doesn't allow consolidation (can_handle_consolidation=0): {0}", [debug_info.jobs_with_invalid_load_type]) + '<br>';
		}
		if (debug_info.jobs_without_addresses > 0) {
			diagnostics_content += __("Jobs without pick/drop addresses: {0}", [debug_info.jobs_without_addresses]) + '<br>';
		}
		if (debug_info.jobs_already_consolidated > 0) {
			diagnostics_content += __("Jobs already in consolidations: {0}", [debug_info.jobs_already_consolidated]) + '<br>';
		}
		if (debug_info.jobs_with_runsheet > 0) {
			diagnostics_content += __("Jobs with run sheets assigned: {0}", [debug_info.jobs_with_runsheet]) + '<br>';
		}
		if (debug_info.company_filter) {
			diagnostics_content += __("Company filter: {0}", [debug_info.company_filter]) + '<br>';
		}
		if (debug_info.consolidation_type_filter) {
			diagnostics_content += __("Consolidation type filter: {0}", [debug_info.consolidation_type_filter]) + '<br>';
		}
		if (debug_info.current_consolidation) {
			diagnostics_content += __("Current consolidation: {0}", [debug_info.current_consolidation]) + '<br>';
		}
		if (debug_info.message) {
			diagnostics_content += '<br><em>' + debug_info.message + '</em><br>';
		}
		
		diagnostics_html = '<div style="margin-top: 15px; border-radius: 4px; border-left: 3px solid #ffc107; background-color: #f8f9fa;">';
		diagnostics_html += '<div class="diagnostics-toggle-header" data-target="' + diagnostics_id + '" style="padding: 10px; cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between;">';
		diagnostics_html += '<strong>' + __("Diagnostics") + '</strong>';
		diagnostics_html += '<i class="fa fa-chevron-down diagnostics-toggle-icon" style="transition: transform 0.2s;"></i>';
		diagnostics_html += '</div>';
		diagnostics_html += '<div id="' + diagnostics_id + '" class="diagnostics-content" style="display: none; padding: 10px; padding-top: 0;">';
		diagnostics_html += diagnostics_content;
		diagnostics_html += '</div>';
		diagnostics_html += '</div>';
	}
	
	const dialog = new frappe.ui.Dialog({
		title: __("Consolidation Suggestions"),
		size: 'large', // Use large size for wider dialog
		fields: [
			{
				fieldname: "summary_info",
				fieldtype: "HTML",
				options: `<div style="margin-bottom: 15px;">
					<p style="font-size: 13px; color: ${has_jobs ? '#6c757d' : '#dc3545'};">
						${has_jobs ? 
							`Found <strong>${jobs.length}</strong> job(s) that can be consolidated.` :
							`<strong>No consolidatable jobs found</strong> matching the criteria.`
						}
						${consolidation_groups && consolidation_groups.length > 0 ? 
							`<br>Grouped into <strong>${consolidation_groups.length}</strong> consolidation group(s).` : 
							(has_jobs ? '<br>No consolidation groups found (jobs may not share common pick/drop addresses).' : '')
						}
					</p>
					${diagnostics_html}
				</div>`
			},
			{
				fieldname: "filter_section_header",
				fieldtype: "HTML",
				options: `<div style="margin: 15px 0 10px 0; border-radius: 4px; border-left: 3px solid #007bff; background-color: #f8f9fa;">
					<div class="filter-toggle-header" data-target="filter_section_content" style="padding: 10px; cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between;">
						<strong>${__("Filters")}</strong>
						<i class="fa fa-chevron-down filter-toggle-icon" style="transition: transform 0.2s; transform: rotate(180deg);"></i>
					</div>
					<div id="filter_section_content" class="filter-content" style="display: block; padding: 0 10px 10px 10px;">
				</div>`
			},
			{
				fieldtype: "Section Break",
				label: ""
			},
			{
				fieldname: "filter_customer",
				fieldtype: "Link",
				label: __("Customer"),
				options: "Customer",
				get_query: function() {
					return {
						filters: {
							name: ["in", unique_customers]
						}
					};
				}
			},
			{
				fieldname: "filter_pick_address",
				fieldtype: "Link",
				label: __("Pick Address"),
				options: "Address",
				get_query: function() {
					return {
						filters: {
							name: ["in", Array.from(all_pick_address_ids)]
						}
					};
				}
			},
			{
				fieldname: "filter_drop_address",
				fieldtype: "Link",
				label: __("Drop Address"),
				options: "Address",
				get_query: function() {
					return {
						filters: {
							name: ["in", Array.from(all_drop_address_ids)]
						}
					};
				}
			},
			{
				fieldname: "filter_consolidation_type",
				fieldtype: "Select",
				label: __("Consolidation Type"),
				options: "Route\nPick\nDrop\nBoth",
				default: frm.doc.consolidation_type || "",
				description: __("Filter jobs by consolidation type pattern. Changes here will update the form field.")
			},
			{
				fieldtype: "Column Break"
			},
			{
				fieldname: "sort_by",
				fieldtype: "Select",
				label: __("Sort By"),
				options: "Job\nCustomer\nScheduled Date\nLoad Type\nPick Address\nDrop Address\nType",
				default: "Scheduled Date",
				description: __("Select field to sort jobs by")
			},
			{
				fieldname: "sort_order",
				fieldtype: "Select",
				label: __("Sort Order"),
				options: "Ascending\nDescending",
				default: "Ascending",
				description: __("Select sort order")
			},
			{
				fieldname: "filter_section_footer",
				fieldtype: "HTML",
				options: `</div></div>`
			},
			{
				fieldtype: "Section Break",
				label: __("Available Jobs")
			},
			{
				fieldname: "view_toggle",
				fieldtype: "HTML",
				options: `
					<div style="margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
						<label style="margin: 0; font-weight: 500;">${__("View:")}</label>
						<div style="display: flex; gap: 5px; align-items: center;">
							<button type="button" class="btn btn-sm view-toggle-btn btn-primary" data-view="jobs" style="min-width: 100px;">
								${__("Jobs")}
							</button>
							<button type="button" class="btn btn-sm view-toggle-btn btn-default" data-view="legs" style="min-width: 100px;">
								${__("Transport Legs")}
							</button>
						</div>
					</div>
				`
			},
			{
				fieldname: "jobs_table",
				fieldtype: "HTML",
				options: build_jobs_table_html(jobs, consolidation_groups)
			},
			...(has_jobs ? [
				{
					fieldtype: "Section Break"
				},
				{
					fieldname: "select_all",
					fieldtype: "Check",
					label: __("Select All"),
					default: 0
				}
			] : [])
		],
		primary_action_label: has_jobs ? __("Add Selected Jobs") : __("Close"),
		primary_action: function(values) {
			if (!has_jobs) {
				dialog.hide();
				return;
			}
			
			// Get selected jobs from checkboxes (works for both jobs and legs view)
			const checkboxes = dialog.$wrapper.find('.job-checkbox:checked');
			selected_jobs = [];
			const selected_job_names = new Set();
			
			checkboxes.each(function() {
				const job_name = $(this).data('job-name');
				if (job_name) {
					selected_job_names.add(job_name);
				}
			});
			
			selected_jobs = Array.from(selected_job_names);
			
			if (selected_jobs.length === 0) {
				frappe.msgprint({
					title: __("No Selection"),
					message: __("Please select at least one job to add."),
					indicator: "orange"
				});
				return;
			}
			
			// Check if document is saved before adding jobs
			if (frm.doc.__islocal) {
				frappe.msgprint({
					title: __("Save Required"),
					message: __("Please save the Transport Consolidation first before adding jobs."),
					indicator: "orange"
				});
				return;
			}
			
			add_jobs_to_consolidation(frm, selected_jobs, dialog);
		}
	});
	
	dialog.show();
	
	// Increase dialog width for better table visibility
	setTimeout(function() {
		if (dialog.$wrapper && dialog.$wrapper.find('.modal-dialog').length) {
			dialog.$wrapper.find('.modal-dialog').css({
				'width': '90%',
				'max-width': '1400px'
			});
		}
	}, 100);
	
	// Setup tooltips after dialog is shown
	if (has_jobs && dialog.fields_dict.jobs_table) {
		setup_address_tooltips(dialog);
	}
	
		// Setup toggle functionality for diagnostics
		setup_diagnostics_toggle(dialog);
	
	// Setup toggle functionality for filters
	setup_filter_toggle(dialog);
	
	// Set initial value of filter_consolidation_type to match form field
	if (dialog.fields_dict.filter_consolidation_type && frm.doc.consolidation_type) {
		dialog.fields_dict.filter_consolidation_type.set_value(frm.doc.consolidation_type);
	}
	
	// Store dialog reference and filter function in form for synchronization
	frm._consolidation_dialog = dialog;
	
	// Initialize dialog variables for legs
	dialog._all_legs = [];
	dialog._filtered_legs = [];
	dialog._current_view = "jobs";
	dialog._legs_job_names = []; // Track which jobs the legs were fetched for
	
	// Initialize jobs data in dialog for use when switching views
	if (!dialog._jobs_data) {
		dialog._jobs_data = {};
	}
	dialog._jobs_data.all_jobs = all_jobs;
	dialog._jobs_data.filtered_jobs = filtered_jobs; // Initialize with current filtered jobs
	
	// Clean up dialog reference when dialog is closed
	const original_hide = dialog.hide;
	dialog.hide = function() {
		if (frm._consolidation_dialog === dialog) {
			frm._consolidation_dialog = null;
		}
		original_hide.call(this);
	};
	
	// Function to filter jobs or legs based on filter values
	function filter_jobs() {
		// First, filter jobs based on filter criteria (this applies to both views)
		const jobs_to_filter = (dialog._jobs_data && dialog._jobs_data.all_jobs) ? dialog._jobs_data.all_jobs : all_jobs;
		
		const filter_customer = dialog.fields_dict.filter_customer ? dialog.fields_dict.filter_customer.get_value() : '';
		const filter_pick_address = dialog.fields_dict.filter_pick_address ? dialog.fields_dict.filter_pick_address.get_value() : '';
		const filter_drop_address = dialog.fields_dict.filter_drop_address ? dialog.fields_dict.filter_drop_address.get_value() : '';
		const filter_consolidation_type = dialog.fields_dict.filter_consolidation_type ? dialog.fields_dict.filter_consolidation_type.get_value() : '';
		
		// Filter jobs (same logic for both views)
		let filtered_jobs_result = jobs_to_filter.filter(function(job) {
			// Filter by customer
			if (filter_customer && job.customer !== filter_customer) {
				return false;
			}
			
			// Filter by pick address (check if any pick address ID matches)
			if (filter_pick_address) {
				const pick_matches = job.pick_addresses && Array.isArray(job.pick_addresses) && 
					job.pick_addresses.some(function(addr) {
						return addr === filter_pick_address;
					});
				if (!pick_matches) {
					return false;
				}
			}
			
			// Filter by drop address (check if any drop address ID matches)
			if (filter_drop_address) {
				const drop_matches = job.drop_addresses && Array.isArray(job.drop_addresses) && 
					job.drop_addresses.some(function(addr) {
						return addr === filter_drop_address;
					});
				if (!drop_matches) {
					return false;
				}
			}
			
			// Note: consolidation_type filtering is done server-side when jobs are fetched
			// So we don't need to filter by it here - the jobs are already filtered
			
			return true;
		});
		
		// Sort jobs (always use 'Scheduled Date' for jobs, 'Date' is only for sorting legs)
		const sort_by = dialog.fields_dict.sort_by ? dialog.fields_dict.sort_by.get_value() : 'Scheduled Date';
		const sort_order = dialog.fields_dict.sort_order ? dialog.fields_dict.sort_order.get_value() : 'Ascending';
		filtered_jobs_result = sort_jobs(filtered_jobs_result, sort_by, sort_order);
		
		// Store filtered jobs in dialog
		if (!dialog._jobs_data) {
			dialog._jobs_data = {};
		}
		dialog._jobs_data.filtered_jobs = filtered_jobs_result;
		
		if (dialog._current_view === "legs") {
			// In legs view: filter jobs first, then get legs for those filtered jobs
			const filtered_job_names = filtered_jobs_result.map(function(job) { return job.name; }).sort();
			const job_names_changed = JSON.stringify(filtered_job_names) !== JSON.stringify(dialog._legs_job_names);
			
			// If job list changed, we need to re-fetch legs for the new filtered jobs
			if (job_names_changed) {
				// Show loading indicator
				if (dialog.fields_dict.jobs_table) {
					dialog.fields_dict.jobs_table.$wrapper.html('<div style="padding: 20px; text-align: center;"><i class="fa fa-spinner fa-spin"></i> ' + __("Loading transport legs...") + '</div>');
				}
				
				// Fetch legs for filtered jobs
				fetch_legs_for_jobs(filtered_job_names, function(legs) {
					dialog._all_legs = legs;
					dialog._legs_job_names = filtered_job_names;
					
					// Sort legs
					dialog._filtered_legs = sort_legs(legs, sort_by, sort_order);
					
					// Update the table
					const table_html = build_legs_table_html(dialog._filtered_legs);
					if (dialog.fields_dict.jobs_table) {
						dialog.fields_dict.jobs_table.$wrapper.html(table_html);
					}
					
					// Update select all checkbox state
					update_select_all_state();
					
					// Update count in summary
					if (dialog.fields_dict.summary_info) {
						const existing_diagnostics = dialog.$wrapper.find('.diagnostics-toggle-header').closest('div').first();
						const diagnostics_html = existing_diagnostics.length > 0 ? existing_diagnostics[0].outerHTML : '';
						
						const summary_html = `<div style="margin-bottom: 15px;">
							<p style="font-size: 13px; color: #6c757d;">
								Found <strong>${dialog._filtered_legs.length}</strong> transport leg(s) from <strong>${filtered_jobs_result.length}</strong> filtered job(s).
							</p>
							${diagnostics_html}
						</div>`;
						dialog.fields_dict.summary_info.$wrapper.html(summary_html);
						
						setup_diagnostics_toggle(dialog);
						setup_filter_toggle(dialog);
					}
				});
			} else {
				// Job list hasn't changed, just sort the existing legs
				dialog._filtered_legs = sort_legs(dialog._all_legs || [], sort_by, sort_order);
				
				// Update the table
				const table_html = build_legs_table_html(dialog._filtered_legs);
				if (dialog.fields_dict.jobs_table) {
					dialog.fields_dict.jobs_table.$wrapper.html(table_html);
				}
				
				// Update select all checkbox state
				update_select_all_state();
				
				// Update count in summary
				if (dialog.fields_dict.summary_info) {
					const existing_diagnostics = dialog.$wrapper.find('.diagnostics-toggle-header').closest('div').first();
					const diagnostics_html = existing_diagnostics.length > 0 ? existing_diagnostics[0].outerHTML : '';
					
					const summary_html = `<div style="margin-bottom: 15px;">
						<p style="font-size: 13px; color: #6c757d;">
							Found <strong>${dialog._filtered_legs.length}</strong> transport leg(s) from <strong>${filtered_jobs_result.length}</strong> filtered job(s).
						</p>
						${diagnostics_html}
					</div>`;
					dialog.fields_dict.summary_info.$wrapper.html(summary_html);
					
					setup_diagnostics_toggle(dialog);
					setup_filter_toggle(dialog);
				}
			}
		} else {
			// In jobs view: use the filtered jobs result
			filtered_jobs = filtered_jobs_result;
			
			// Update the table
			const table_html = build_jobs_table_html(filtered_jobs, consolidation_groups);
			if (dialog.fields_dict.jobs_table) {
				dialog.fields_dict.jobs_table.$wrapper.html(table_html);
				setup_address_tooltips(dialog);
			}
			
			// Update select all checkbox state
			update_select_all_state();
			
			// Update count in summary (preserve diagnostics if it exists)
			if (dialog.fields_dict.summary_info) {
				const existing_diagnostics = dialog.$wrapper.find('.diagnostics-toggle-header').closest('div').first();
				const diagnostics_html = existing_diagnostics.length > 0 ? existing_diagnostics[0].outerHTML : '';
				
				const summary_html = `<div style="margin-bottom: 15px;">
					<p style="font-size: 13px; color: #6c757d;">
						Found <strong>${filtered_jobs.length}</strong> job(s) that can be consolidated.
						${consolidation_groups && consolidation_groups.length > 0 ? 
							`<br>Grouped into <strong>${consolidation_groups.length}</strong> consolidation group(s).` : ''}
					</p>
					${diagnostics_html}
				</div>`;
				dialog.fields_dict.summary_info.$wrapper.html(summary_html);
				
				// Re-setup toggle functionality after updating HTML
				setup_diagnostics_toggle(dialog);
				
				// Re-setup filter toggle functionality
				setup_filter_toggle(dialog);
			}
		}
	}
	
	// Store filter_jobs function reference in dialog for external access
	dialog._filter_jobs = filter_jobs;
	
	// Function to switch between jobs and legs view
	function switch_view(view_type) {
		current_view = view_type;
		dialog._current_view = view_type;
		
		// Update toggle buttons
		dialog.$wrapper.find('.view-toggle-btn').removeClass('btn-primary').addClass('btn-default');
		dialog.$wrapper.find(`.view-toggle-btn[data-view="${view_type}"]`).removeClass('btn-default').addClass('btn-primary');
		
		// Update section label
		const section_label = dialog.$wrapper.find('label:contains("Available Jobs"), label:contains("Available Transport Legs")').closest('.form-section').find('label');
		if (view_type === "legs") {
			section_label.text(__("Available Transport Legs"));
		} else {
			section_label.text(__("Available Jobs"));
		}
		
		// Note: Sort options are kept the same for both views
		// The sort functions will handle the mapping appropriately
		
		if (view_type === "legs") {
			// Switch to legs view
			// Get currently filtered/visible jobs from the Jobs view
			const jobs_to_use = (dialog._jobs_data && dialog._jobs_data.filtered_jobs) ? 
				dialog._jobs_data.filtered_jobs : filtered_jobs;
			const current_job_names = jobs_to_use.map(function(job) { return job.name; }).sort();
			
			// Check if we need to fetch legs (either not fetched yet, or job list has changed)
			const job_names_changed = JSON.stringify(current_job_names) !== JSON.stringify(dialog._legs_job_names);
			
			if (!dialog._all_legs || dialog._all_legs.length === 0 || job_names_changed) {
				// Fetch legs for currently visible/filtered jobs
				dialog.fields_dict.jobs_table.$wrapper.html('<div style="padding: 20px; text-align: center;"><i class="fa fa-spinner fa-spin"></i> ' + __("Loading transport legs...") + '</div>');
				
				fetch_legs_for_jobs(current_job_names, function(legs) {
					dialog._all_legs = legs;
					dialog._filtered_legs = legs;
					dialog._legs_job_names = current_job_names; // Store which jobs we fetched legs for
					
					// Apply current filters to legs
					if (dialog._filter_jobs) {
						dialog._filter_jobs();
					} else {
						// Update table directly
						const table_html = build_legs_table_html(dialog._filtered_legs);
						dialog.fields_dict.jobs_table.$wrapper.html(table_html);
						update_select_all_state();
					}
				});
			} else {
				// Legs already fetched for current job list, just update the table
				if (dialog._filter_jobs) {
					dialog._filter_jobs();
				} else {
					const table_html = build_legs_table_html(dialog._filtered_legs);
					dialog.fields_dict.jobs_table.$wrapper.html(table_html);
					update_select_all_state();
				}
			}
		} else {
			// Switch to jobs view
			if (dialog._filter_jobs) {
				dialog._filter_jobs();
			} else {
				const table_html = build_jobs_table_html(filtered_jobs, consolidation_groups);
				dialog.fields_dict.jobs_table.$wrapper.html(table_html);
				setup_address_tooltips(dialog);
				update_select_all_state();
			}
		}
	}
	
	// Store switch_view function in dialog
	dialog._switch_view = switch_view;
	
	// Wait for dialog to render, then set up event handlers (always set up, even when no jobs)
	setTimeout(function() {
		// Set up view toggle buttons
		dialog.$wrapper.on('click', '.view-toggle-btn', function() {
			const view_type = $(this).data('view');
			switch_view(view_type);
		});
		
		// Set up filter change handlers
		// For Link fields, use a combination of events to catch all changes
		function setup_link_field_handler(field) {
			if (!field) return;
			
			// Listen to input change
			if (field.$input) {
				field.$input.on('change', filter_jobs);
			}
			
			// Listen to the autocomplete selection (for Link fields)
			field.$wrapper.on('change', 'input', filter_jobs);
			
			// Override set_value to trigger filter
			const original_set_value = field.set_value;
			if (original_set_value) {
				field.set_value = function(value) {
					const result = original_set_value.call(this, value);
					setTimeout(filter_jobs, 100);
					return result;
				};
			}
		}
		
		setup_link_field_handler(dialog.fields_dict.filter_customer);
		setup_link_field_handler(dialog.fields_dict.filter_pick_address);
		setup_link_field_handler(dialog.fields_dict.filter_drop_address);
		
		// For Select fields, use standard change event
		if (dialog.fields_dict.filter_consolidation_type) {
			// Store flag in dialog to prevent recursive updates
			dialog._updating_from_dialog = false;
			dialog.fields_dict.filter_consolidation_type.$input.on('change', function() {
				// Update form field when dialog filter changes
				const new_value = dialog.fields_dict.filter_consolidation_type.get_value() || "";
				if (frm.doc.consolidation_type !== new_value && !dialog._updating_from_dialog) {
					dialog._updating_from_dialog = true;
					frm.set_value("consolidation_type", new_value);
					setTimeout(function() {
						dialog._updating_from_dialog = false;
					}, 200);
				}
				// Re-fetch jobs from server with new consolidation_type filter
				// This is necessary because the backend filters jobs based on consolidation_type
				reload_jobs_with_filter(frm, dialog, new_value);
			});
		}
		
		// Handle sort fields
		if (dialog.fields_dict.sort_by) {
			dialog.fields_dict.sort_by.$input.on('change', filter_jobs);
		}
		if (dialog.fields_dict.sort_order) {
			dialog.fields_dict.sort_order.$input.on('change', filter_jobs);
		}
		
		// Handle select all checkbox in table header
		dialog.$wrapper.on('change', '.select-all-checkbox', function() {
			const checked = $(this).is(':checked');
			dialog.$wrapper.find('.job-checkbox').prop('checked', checked);
			// Also update the dialog's select_all field if it exists
			if (dialog.fields_dict.select_all) {
				dialog.fields_dict.select_all.set_value(checked);
			}
		});
		
		// Handle select all checkbox (only if it exists)
		if (dialog.fields_dict.select_all) {
			dialog.fields_dict.select_all.$input.on('change', function() {
				const checked = $(this).is(':checked');
				dialog.$wrapper.find('.job-checkbox').prop('checked', checked);
				// Also update the table header checkbox
				dialog.$wrapper.find('.select-all-checkbox').prop('checked', checked);
			});
		}
		
		// Handle individual checkboxes
		dialog.$wrapper.on('change', '.job-checkbox', function() {
			update_select_all_state();
		});
	
		function update_select_all_state() {
			const total = dialog.$wrapper.find('.job-checkbox').length;
			const checked = dialog.$wrapper.find('.job-checkbox:checked').length;
			const all_checked = checked === total && total > 0;
			// Update both checkboxes
			if (dialog.fields_dict.select_all) {
				dialog.fields_dict.select_all.set_value(all_checked);
			}
			dialog.$wrapper.find('.select-all-checkbox').prop('checked', all_checked);
		}
	}, 100);
}

function sort_legs(legs, sort_by, sort_order) {
	if (!legs || legs.length === 0) {
		return legs;
	}
	
	const is_ascending = sort_order === 'Ascending';
	const sorted_legs = [...legs];
	
	sorted_legs.sort(function(a, b) {
		let a_value, b_value;
		
		// Map job sort options to leg fields
		switch(sort_by) {
			case 'Leg':
			case 'Job':  // For legs view, "Job" means leg name, but we'll use transport_job
				if (sort_by === 'Leg') {
					a_value = a.name || '';
					b_value = b.name || '';
				} else {
					a_value = a.transport_job || '';
					b_value = b.transport_job || '';
				}
				break;
			case 'Customer':
				a_value = a.customer || '';
				b_value = b.customer || '';
				break;
			case 'Date':
			case 'Scheduled Date':  // Map "Scheduled Date" to leg date
				a_value = a.date || a.run_date || a.scheduled_date || '';
				b_value = b.date || b.run_date || b.scheduled_date || '';
				if (!a_value && !b_value) return 0;
				if (!a_value) return is_ascending ? 1 : -1;
				if (!b_value) return is_ascending ? -1 : 1;
				const date_compare = a_value.localeCompare(b_value);
				return is_ascending ? date_compare : -date_compare;
			case 'Load Type':
				a_value = a.load_type || '';
				b_value = b.load_type || '';
				break;
			case 'Pick Address':
				a_value = (a.pick_address_title || a.pick_address || '').toLowerCase();
				b_value = (b.pick_address_title || b.pick_address || '').toLowerCase();
				break;
			case 'Drop Address':
				a_value = (a.drop_address_title || a.drop_address || '').toLowerCase();
				b_value = (b.drop_address_title || b.drop_address || '').toLowerCase();
				break;
			case 'Status':
				a_value = a.status || '';
				b_value = b.status || '';
				break;
			case 'Type':  // For legs, type doesn't apply, sort by status instead
				a_value = a.status || '';
				b_value = b.status || '';
				break;
			default:
				a_value = '';
				b_value = '';
		}
		
		if (typeof a_value === 'string' && sort_by !== 'Date' && sort_by !== 'Scheduled Date') {
			a_value = a_value.toLowerCase();
		}
		if (typeof b_value === 'string' && sort_by !== 'Date' && sort_by !== 'Scheduled Date') {
			b_value = b_value.toLowerCase();
		}
		
		if (a_value < b_value) {
			return is_ascending ? -1 : 1;
		}
		if (a_value > b_value) {
			return is_ascending ? 1 : -1;
		}
		return 0;
	});
	
	return sorted_legs;
}

function sort_jobs(jobs, sort_by, sort_order) {
	if (!jobs || jobs.length === 0) {
		return jobs;
	}
	
	const is_ascending = sort_order === 'Ascending';
	
	// Create a copy to avoid mutating the original array
	const sorted_jobs = [...jobs];
	
	sorted_jobs.sort(function(a, b) {
		let a_value, b_value;
		
		// Get values based on sort_by field
		switch(sort_by) {
			case 'Job':
				a_value = a.name || '';
				b_value = b.name || '';
				break;
			case 'Customer':
				a_value = a.customer || '';
				b_value = b.customer || '';
				break;
			case 'Scheduled Date':
				// Handle date sorting - convert to comparable format
				a_value = a.scheduled_date || '';
				b_value = b.scheduled_date || '';
				// Handle empty dates - put them at the end
				if (!a_value && !b_value) return 0;
				if (!a_value) return is_ascending ? 1 : -1;
				if (!b_value) return is_ascending ? -1 : 1;
				// If dates are strings, compare them directly (ISO format YYYY-MM-DD)
				const date_compare = a_value.localeCompare(b_value);
				return is_ascending ? date_compare : -date_compare;
			case 'Load Type':
				a_value = a.load_type || '';
				b_value = b.load_type || '';
				break;
			case 'Pick Address':
				a_value = a.pick_address || '';
				b_value = b.pick_address || '';
				break;
			case 'Drop Address':
				a_value = a.drop_address || '';
				b_value = b.drop_address || '';
				break;
			case 'Type':
				a_value = a.consolidation_type || '';
				b_value = b.consolidation_type || '';
				break;
			default:
				a_value = '';
				b_value = '';
		}
		
		// Convert to strings for comparison
		a_value = String(a_value || '').toLowerCase();
		b_value = String(b_value || '').toLowerCase();
		
		// Compare values
		if (a_value < b_value) {
			return is_ascending ? -1 : 1;
		}
		if (a_value > b_value) {
			return is_ascending ? 1 : -1;
		}
		return 0;
	});
	
	return sorted_jobs;
}

function build_legs_table_html(legs) {
	if (!legs || legs.length === 0) {
		return `
			<div style="padding: 20px; text-align: center; color: #6c757d;">
				<p>${__("No transport legs available to display.")}</p>
			</div>
		`;
	}
	
	// Add custom tooltip CSS styles (reuse from jobs table)
	const tooltip_css = `
		<style>
			.address-tooltip-container {
				position: relative;
				max-height: 400px;
				overflow-y: auto;
				overflow-x: auto;
				border: 1px solid #d1d5db;
				border-radius: 4px;
				width: 100%;
				box-sizing: border-box;
			}
			.address-tooltip-container table {
				width: 100%;
				table-layout: fixed;
				margin: 0;
				border-collapse: collapse;
			}
			.address-tooltip-container table th,
			.address-tooltip-container table td {
				word-wrap: break-word;
				overflow-wrap: break-word;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.address-tooltip-container table td {
				max-width: 0;
			}
		</style>
	`;
	
	let html = tooltip_css + `
		<div class="address-tooltip-container">
			<table class="table table-bordered table-condensed" style="font-size: 12px; margin: 0;">
				<thead>
					<tr style="background-color: #f8f9fa;">
						<th style="width: 40px; text-align: center; padding: 8px;">
							<input type="checkbox" class="select-all-checkbox">
						</th>
						<th style="width: 10%; padding: 8px;">${__("Leg")}</th>
						<th style="width: 10%; padding: 8px;">${__("Job")}</th>
						<th style="width: 12%; padding: 8px;">${__("Customer")}</th>
						<th style="width: 10%; padding: 8px;">${__("Date")}</th>
						<th style="width: 10%; padding: 8px;">${__("Load Type")}</th>
						<th style="width: 18%; padding: 8px;">${__("Pick Address")}</th>
						<th style="width: 18%; padding: 8px;">${__("Drop Address")}</th>
						<th style="width: 8%; padding: 8px;">${__("Status")}</th>
					</tr>
				</thead>
				<tbody>
	`;
	
	legs.forEach(function(leg) {
		// Format date
		let date_display = '-';
		if (leg.date) {
			date_display = frappe.datetime.str_to_user(leg.date);
		} else if (leg.run_date) {
			date_display = frappe.datetime.str_to_user(leg.run_date);
		}
		
		// Get address display
		const pick_address_display = leg.pick_address_title || leg.pick_address || '-';
		const drop_address_display = leg.drop_address_title || leg.drop_address || '-';
		
		// Status badge
		let status_badge = leg.status || 'Open';
		let status_class = 'badge-secondary';
		if (status_badge === 'Completed') {
			status_class = 'badge-success';
		} else if (status_badge === 'Started') {
			status_class = 'badge-info';
		} else if (status_badge === 'Assigned') {
			status_class = 'badge-primary';
		}
		
		html += `
			<tr>
				<td style="text-align: center; padding: 8px;">
					<input type="checkbox" class="job-checkbox" data-job-name="${leg.transport_job}" data-leg-name="${leg.name}">
				</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
					<a href="/app/transport-leg/${leg.name}" target="_blank">${leg.name}</a>
				</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
					<a href="/app/transport-job/${leg.transport_job}" target="_blank">${leg.transport_job || '-'}</a>
				</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${leg.customer || '-'}">${leg.customer || '-'}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${date_display}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${leg.load_type || '-'}">${leg.load_type || '-'}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${pick_address_display}">${pick_address_display}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${drop_address_display}">${drop_address_display}</td>
				<td style="padding: 8px;">
					<span class="badge ${status_class}">${status_badge}</span>
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

function build_jobs_table_html(jobs, consolidation_groups) {
	if (!jobs || jobs.length === 0) {
		return `
			<div style="padding: 20px; text-align: center; color: #6c757d;">
				<p>${__("No consolidatable jobs available to display.")}</p>
			</div>
		`;
	}
	
	// Add custom tooltip CSS styles
	const tooltip_css = `
		<style>
			.address-tooltip-container {
				position: relative;
				max-height: 400px;
				overflow-y: auto;
				overflow-x: auto;
				border: 1px solid #d1d5db;
				border-radius: 4px;
				width: 100%;
				box-sizing: border-box;
			}
			.address-tooltip-container table {
				width: 100%;
				table-layout: fixed;
				margin: 0;
				border-collapse: collapse;
			}
			.address-tooltip-container table th,
			.address-tooltip-container table td {
				word-wrap: break-word;
				overflow-wrap: break-word;
				overflow: hidden;
				text-overflow: ellipsis;
			}
			.address-tooltip-container table td {
				max-width: 0;
			}
			.address-tooltip-wrapper {
				position: relative;
				display: inline-block;
				cursor: pointer;
				width: 100%;
				z-index: 1;
			}
			.address-tooltip {
				visibility: hidden;
				opacity: 0;
				position: fixed;
				background: #ff9800;
				color: #fff;
				padding: 12px 16px;
				border-radius: 8px;
				white-space: normal;
				z-index: 10000;
				box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
				transition: opacity 0.2s, visibility 0.2s;
				pointer-events: none;
				font-size: 13px;
				line-height: 1.6;
				min-width: 200px;
				max-width: 300px;
			}
			.address-tooltip::after {
				content: '';
				position: absolute;
				top: 100%;
				left: 20px;
				border: 8px solid transparent;
				border-top-color: #ff9800;
			}
			.address-tooltip-wrapper:hover .address-tooltip {
				visibility: visible;
				opacity: 1;
			}
			.address-tooltip-list {
				list-style: none;
				padding: 0;
				margin: 0;
				white-space: normal;
			}
			.address-tooltip-list li {
				margin: 4px 0;
				padding: 0;
				color: #fff;
			}
		</style>
	`;
	
	let html = tooltip_css + `
		<div class="address-tooltip-container">
			<table class="table table-bordered table-condensed" style="font-size: 12px; margin: 0;">
				<thead>
					<tr style="background-color: #f8f9fa;">
						<th style="width: 40px; text-align: center; padding: 8px;">
							<input type="checkbox" class="select-all-checkbox">
						</th>
						<th style="width: 12%; padding: 8px;">${__("Job")}</th>
						<th style="width: 15%; padding: 8px;">${__("Customer")}</th>
						<th style="width: 12%; padding: 8px;">${__("Scheduled Date")}</th>
						<th style="width: 10%; padding: 8px;">${__("Load Type")}</th>
						<th style="width: 18%; padding: 8px;">${__("Pick Address")}</th>
						<th style="width: 18%; padding: 8px;">${__("Drop Address")}</th>
						<th style="width: 10%; padding: 8px;">${__("Type")}</th>
					</tr>
				</thead>
				<tbody>
	`;
	
	// Helper function to escape HTML
	function escapeHtml(text) {
		if (!text) return '';
		const map = {
			'&': '&amp;',
			'<': '&lt;',
			'>': '&gt;',
			'"': '&quot;',
			"'": '&#039;'
		};
		return text.replace(/[&<>"']/g, m => map[m]);
	}
	
	jobs.forEach(function(job) {
		let consolidation_badge = '-';
		if (job.consolidation_type === 'Pick') {
			consolidation_badge = '<span class="badge badge-info" style="background-color: #007bff;">Pick</span>';
		} else if (job.consolidation_type === 'Drop') {
			consolidation_badge = '<span class="badge badge-success" style="background-color: #28a745;">Drop</span>';
		} else if (job.consolidation_type === 'Both') {
			consolidation_badge = '<span class="badge badge-warning" style="background-color: #ffc107;">Both</span>';
		} else if (job.consolidation_type === 'Route') {
			consolidation_badge = '<span class="badge badge-secondary" style="background-color: #6c757d;">Route</span>';
		}
		
		// Show consolidation status if some legs are already consolidated
		let consolidation_status = '';
		if (job.has_partial_consolidation) {
			consolidation_status = `<span class="badge badge-warning" style="background-color: #ff9800;" title="${__('Some legs are already consolidated')}">
				${__('Partial')} (${job.available_legs_count}/${job.legs_count})
			</span>`;
		}
		
		// Build tooltip for Route consolidation type or blank consolidation type with multiple addresses
		let pick_address_cell = job.pick_address || '-';
		let drop_address_cell = job.drop_address || '-';
		let pick_address_tooltip_html = '';
		let drop_address_tooltip_html = '';
		
		// Show tooltip with all addresses when consolidation_type is Route or blank/empty and there are multiple addresses
		const is_route_or_blank = job.consolidation_type === 'Route' || !job.consolidation_type || job.consolidation_type === '';
		if (is_route_or_blank) {
			// Check if there are multiple pick addresses (indicated by "X different" text or multiple titles)
			const has_multiple_pick = job.pick_address && job.pick_address.includes('different');
			if (has_multiple_pick && job.pick_address_titles && job.pick_address_titles.length > 1) {
				// Create numbered list HTML for tooltip
				const pick_list_items = job.pick_address_titles.map((addr, idx) => 
					`<li>${idx + 1}. ${escapeHtml(addr)}</li>`
				).join('');
				pick_address_tooltip_html = `<ul class="address-tooltip-list">${pick_list_items}</ul>`;
			}
			
			// Check if there are multiple drop addresses (indicated by "X different" text or multiple titles)
			const has_multiple_drop = job.drop_address && job.drop_address.includes('different');
			if (has_multiple_drop && job.drop_address_titles && job.drop_address_titles.length > 1) {
				// Create numbered list HTML for tooltip
				const drop_list_items = job.drop_address_titles.map((addr, idx) => 
					`<li>${idx + 1}. ${escapeHtml(addr)}</li>`
				).join('');
				drop_address_tooltip_html = `<ul class="address-tooltip-list">${drop_list_items}</ul>`;
			}
		}
		
		// Build pick address cell with tooltip if needed
		let pick_cell_html = '';
		if (pick_address_tooltip_html) {
			pick_cell_html = `
				<div class="address-tooltip-wrapper" style="display: inline-block; width: 100%;">
					<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${pick_address_cell}</div>
					<div class="address-tooltip">${pick_address_tooltip_html}</div>
				</div>
			`;
		} else {
			pick_cell_html = `<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${pick_address_cell}">${pick_address_cell}</div>`;
		}
		
		// Build drop address cell with tooltip if needed
		let drop_cell_html = '';
		if (drop_address_tooltip_html) {
			drop_cell_html = `
				<div class="address-tooltip-wrapper" style="display: inline-block; width: 100%;">
					<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${drop_address_cell}</div>
					<div class="address-tooltip">${drop_address_tooltip_html}</div>
				</div>
			`;
		} else {
			drop_cell_html = `<div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${drop_address_cell}">${drop_address_cell}</div>`;
		}
		
		// Format scheduled date
		let scheduled_date_display = '-';
		if (job.scheduled_date) {
			scheduled_date_display = frappe.datetime.str_to_user(job.scheduled_date);
		}
		
		html += `
			<tr>
				<td style="text-align: center; padding: 8px;">
					<input type="checkbox" class="job-checkbox" data-job-name="${job.name}">
				</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
					<a href="/app/transport-job/${job.name}" target="_blank">${job.name}</a>
					${consolidation_status ? '<br>' + consolidation_status : ''}
				</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${job.customer || '-'}">${job.customer || '-'}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${scheduled_date_display}</td>
				<td style="padding: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${job.load_type || '-'}">${job.load_type || '-'}</td>
				<td style="padding: 8px;">${pick_cell_html}</td>
				<td style="padding: 8px;">${drop_cell_html}</td>
				<td style="padding: 8px;">${consolidation_badge}</td>
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
	// Check if document is saved before creating Run Sheet
	if (frm.doc.__islocal) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Transport Consolidation first before creating a Run Sheet."),
			indicator: "orange"
		});
		return;
	}
	
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
