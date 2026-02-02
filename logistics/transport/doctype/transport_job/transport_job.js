// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Helper function to apply load_type filters (same pattern as vehicle_type)
function apply_load_type_filters(frm, preserve_existing_value) {
	// Filter load types based on transport job type and boolean columns
	// preserve_existing_value: if true, don't clear load_type even if not in filtered list (used during refresh)
	if (!frm.doc.transport_job_type) {
		// Clear filters if no job type selected
		frm.set_df_property('load_type', 'filters', {});
		return;
	}

	// Build filters based on job type
	var filters = {
		transport: 1
	};
	
	// Map transport_job_type to Load Type boolean field
	if (frm.doc.transport_job_type === "Container") {
		filters.container = 1;
	} else if (frm.doc.transport_job_type === "Non-Container") {
		filters.non_container = 1;
	} else if (frm.doc.transport_job_type === "Special") {
		filters.special = 1;
	} else if (frm.doc.transport_job_type === "Oversized") {
		filters.oversized = 1;
	} else if (frm.doc.transport_job_type === "Heavy Haul") {
		filters.heavy_haul = 1;
	} else if (frm.doc.transport_job_type === "Multimodal") {
		filters.multimodal = 1;
	}

	// Apply filters to load_type field
	frm.set_df_property('load_type', 'filters', filters);
	
	// Only clear load_type if current selection is not in filtered list
	// AND we're not preserving existing values (i.e., during refresh after save)
	if (!preserve_existing_value && frm.doc.load_type) {
		// Validate if current load_type is still allowed
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Load Type",
				name: frm.doc.load_type
			},
			callback: function(r) {
				if (r.message) {
					const load_type_doc = r.message;
					const field_map = {
						"Container": "container",
						"Non-Container": "non_container",
						"Special": "special",
						"Oversized": "oversized",
						"Multimodal": "multimodal",
						"Heavy Haul": "heavy_haul"
					};
					const allowed_field = field_map[frm.doc.transport_job_type];
					if (allowed_field && !load_type_doc[allowed_field]) {
						frm.set_value('load_type', '');
					}
				}
			}
		});
	}
	
	// Refresh the field to apply filters
	frm.refresh_field('load_type');
}

frappe.ui.form.on('Transport Job', {
	setup: function(frm) {
		// Set default transport_job_type for new documents immediately
		// This must happen in setup (before onload) to prevent validation errors
		if (frm.is_new() && !frm.doc.transport_job_type) {
			frm.doc.transport_job_type = 'Non-Container';
		}
		// Set default status for new documents immediately
		if (frm.is_new() && !frm.doc.status) {
			frm.doc.status = 'Draft';
		}
		// Apply load_type filters before field is ever used
		apply_load_type_filters(frm);
		// Update consolidate checkbox visibility
		frm.events.toggle_consolidate_visibility(frm);
	},

	onload: function(frm) {
		// Ensure transport_job_type is always set
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		// Ensure status is always set (defaults to Draft for new documents)
		if (!frm.doc.status) {
			frm.set_value('status', 'Draft');
		}
		// Initialize previous status tracking
		frm._previous_status = frm.doc.status;
		// Update container fields visibility
		frm.events.toggle_container_fields(frm);
		// Update consolidate checkbox visibility
		frm.events.toggle_consolidate_visibility(frm);
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		// Apply load_type filters on load (preserve existing values for existing documents)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, !frm.is_new());
		}
		// Fetch scheduled_date from Transport Order if transport_order is set and scheduled_date is empty
		if (frm.doc.transport_order && !frm.doc.scheduled_date) {
			frm.events.fetch_scheduled_date_from_transport_order(frm);
		}
	},

	refresh: function(frm) {
		// Ensure transport_job_type is always set
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		// Ensure status is always set (defaults to Draft for new documents)
		if (!frm.doc.status) {
			frm.set_value('status', 'Draft');
		}
		// Initialize previous status tracking if not set
		if (frm._previous_status === undefined) {
			frm._previous_status = frm.doc.status;
		}
		// Update container fields visibility
		frm.events.toggle_container_fields(frm);
		// Update consolidate checkbox visibility
		frm.events.toggle_consolidate_visibility(frm);
		// Update vehicle_type required state based on consolidate checkbox
		frm.events.toggle_vehicle_type_required(frm);
		// Apply load_type filters on refresh (preserve existing values)
		if (frm.doc.transport_job_type) {
			apply_load_type_filters(frm, true);
		}
		
		// Clean up realtime listener if document is no longer submitted
		if (frm._status_realtime_listener && (!frm.doc.docstatus || frm.doc.docstatus !== 1)) {
			frappe.realtime.off('transport_job_status_changed', frm._status_realtime_listener);
			frm._status_realtime_listener = null;
		}
		
		// Set up realtime event listener for status updates
		// Status updates happen automatically via triggers (Transport Leg changes, document lifecycle hooks)
		// When a transport leg card is started from Run Sheet, the status changes to "In Progress" server-side
		// The trigger flow: Run Sheet -> startTransportLeg() -> set_dates_and_update_status() -> 
		// Transport Leg after_save() -> update_transport_job_status() -> Transport Job status = "In Progress"
		// -> frappe.publish_realtime('transport_job_status_changed') -> client receives event
		if (!frm.is_new() && frm.doc.docstatus === 1) {
			// Clean up any existing realtime listener
			if (frm._status_realtime_listener) {
				frappe.realtime.off('transport_job_status_changed', frm._status_realtime_listener);
				frm._status_realtime_listener = null;
			}
			
			// Set up realtime event listener for status changes
			frm._status_realtime_listener = function(data) {
				// Only process events for this specific Transport Job
				if (!frm || frm.is_destroyed || !frm.doc || data.job_name !== frm.doc.name) {
					return;
				}
				
				// Only process if document is still submitted
				if (frm.doc.docstatus !== 1) {
					// Clean up listener if document is no longer submitted
					if (frm._status_realtime_listener) {
						frappe.realtime.off('transport_job_status_changed', frm._status_realtime_listener);
						frm._status_realtime_listener = null;
					}
					return;
				}
				
				const previous_status = frm.doc.status;
				const new_status = data.status;
				
				// Update the document's status value directly
				if (new_status && new_status !== frm.doc.status) {
					frm.doc.status = new_status;
					
					// Trigger status change handler if status changed to "In Progress"
					// This happens when a transport leg card is started from Run Sheet
					if (new_status === 'In Progress' && previous_status !== 'In Progress') {
						frm.events.on_status_in_progress(frm, previous_status);
					}
					// Trigger status change handler if status changed to "Completed"
					// This happens when all transport legs are completed
					if (new_status === 'Completed' && previous_status !== 'Completed') {
						frm.events.on_status_completed(frm, previous_status);
					}
					
					// Update docstatus if it changed
					if (data.docstatus !== undefined && data.docstatus !== frm.doc.docstatus) {
						frm.doc.docstatus = data.docstatus;
						// If document is no longer submitted, clean up listener
						if (data.docstatus !== 1) {
							if (frm._status_realtime_listener) {
								frappe.realtime.off('transport_job_status_changed', frm._status_realtime_listener);
								frm._status_realtime_listener = null;
							}
						}
					}
					
					// Refresh status field to ensure UI is up-to-date
					frm.refresh_field('status');
					
					// Update previous status tracking
					frm._previous_status = new_status;
				}
			};
			
			// Register the realtime event listener
			frappe.realtime.on('transport_job_status_changed', frm._status_realtime_listener);
		} else if (!frm.is_new() && frm.doc.docstatus === 0) {
			// For draft documents, ensure status is set correctly
			// If docstatus is 0 but status is not Draft, it might need correction
			if (frm.doc.status && frm.doc.status !== 'Draft') {
				// Fetch from database to ensure consistency
				frappe.db.get_value('Transport Job', frm.doc.name, 'status', (r) => {
					if (r && r.status) {
						frm.doc.status = r.status;
						frm.refresh_field('status');
					}
				});
			} else {
				// Refresh status field to ensure it displays the current value
				frm.refresh_field('status');
			}
		} else {
			// For new documents, just refresh the status field
			frm.refresh_field('status');
		}
		
		// Check run sheet statuses and update Transport Job status if needed
		// Status should be "In Progress" if any run sheet has status "Dispatched", "In-Progress", or "Hold"
		if (frm.doc.legs && frm.doc.legs.length > 0 && !frm.is_new() && frm.doc.docstatus === 1) {
			frm.events.check_run_sheet_statuses(frm);
		}
		
		// Fetch and update missing data from Transport Leg
		frm.events.update_legs_missing_data(frm);
		
		// Automatically update run_sheet from consolidation if available (works for submitted docs too)
		if (frm.doc.legs && frm.doc.legs.length > 0 && !frm.is_new()) {
			frappe.call({
				method: "logistics.transport.doctype.transport_job.transport_job.update_run_sheet_from_consolidation",
				args: {
					job_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.updated_count > 0) {
						// Reload the form to show updated run_sheet values
						frm.reload_doc();
					}
				},
				error: function(r) {
					// Silently fail - don't show error to user
				}
			});
		}
		
		// Automatically update run_sheet from Transport Leg if available (works for submitted docs too)
		// This ensures that when a Run Sheet is created from a Transport Job, the run_sheet field
		// in the legs child table is populated dynamically from the Transport Leg
		if (frm.doc.legs && frm.doc.legs.length > 0 && !frm.is_new()) {
			frappe.call({
				method: "logistics.transport.doctype.transport_job.transport_job.update_run_sheet_from_transport_leg",
				args: {
					job_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.updated_count > 0) {
						// Reload the form to show updated run_sheet values
						frm.reload_doc();
					}
				},
				error: function(r) {
					// Silently fail - don't show error to user
				}
			});
		}
		
		// Add button to manually fetch missing leg data (works for submitted docs too)
		if (frm.doc.legs && frm.doc.legs.length > 0) {
			frm.add_custom_button(__('Fetch Missing Leg Data'), function() {
				frm.events.fetch_missing_leg_data_server(frm);
			}, __('Actions'));
		}
		
		// Add button to create Run Sheet (only for submitted documents and if no Run Sheet exists)
		if (!frm.is_new() && frm.doc.docstatus === 1) {
			// Check if any leg already has a run_sheet assigned
			const has_existing_run_sheet = frm.doc.legs && frm.doc.legs.some(leg => leg.run_sheet);
			
			if (!has_existing_run_sheet) {
				frm.add_custom_button(__('Run Sheet'), function() {
					frm.events.create_run_sheet(frm);
				}, __('Create'));
			}
		}
		
		// Status is automatically updated via trigger-based hooks (document lifecycle and Transport Leg changes)
		// No need for manual "Fix Status" button - status updates happen automatically when triggered
		
		// Lalamove Integration
		if (frm.doc.use_lalamove && !frm.is_new()) {
			frm.add_custom_button(__('Lalamove'), function() {
				// Load Lalamove utilities if not already loaded
				if (typeof logistics === 'undefined' || !logistics.lalamove) {
					frappe.require('/assets/logistics/lalamove/utils.js', function() {
						frappe.require('/assets/logistics/lalamove/lalamove_form.js', function() {
							logistics.lalamove.form.showLalamoveDialog(frm);
						});
					});
				} else {
					logistics.lalamove.form.showLalamoveDialog(frm);
				}
			}, __('Actions'));
			
			// Show order status indicator if order exists
			if (frm.doc.lalamove_order) {
				frappe.db.get_value('Lalamove Order', frm.doc.lalamove_order, ['status', 'lalamove_order_id'], (r) => {
					if (r && r.status) {
						const status_color = r.status === 'COMPLETED' ? 'green' : (r.status === 'CANCELLED' ? 'red' : 'blue');
						frm.dashboard.add_indicator(__('Lalamove: {0}', [r.status]), status_color);
					}
				});
			}
		}
		
		// Add Create Sales Invoice button under Actions menu
		// Only show for submitted documents with "Completed" status without existing sales invoice
		if (!frm.is_new() && frm.doc.docstatus === 1 && frm.doc.status === 'Completed' && !frm.doc.sales_invoice) {
			frm.add_custom_button(__('Create Sales Invoice'), function() {
				frm.events.create_sales_invoice_manual(frm);
			}, __('Actions'));
		}
	},

	transport_job_type: function(frm) {
		// Update container fields visibility when transport_job_type changes
		frm.events.toggle_container_fields(frm);
		// Update consolidate checkbox visibility when transport_job_type changes
		frm.events.toggle_consolidate_visibility(frm);
		// Apply load_type filters (same pattern as vehicle_type)
		apply_load_type_filters(frm);
		// Clear invalid value when job type changes
		frm.set_value('load_type', null);
	},

	consolidate: function(frm) {
		// Update vehicle_type required state when consolidate checkbox changes
		frm.events.toggle_vehicle_type_required(frm);
	},

	transport_order: function(frm) {
		// Check for duplicate Transport Jobs when transport_order is set
		if (frm.doc.transport_order && frm.is_new()) {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Transport Job',
					filters: {
						transport_order: frm.doc.transport_order,
						name: ['!=', frm.doc.name || '']
					},
					fields: ['name'],
					limit: 1
				},
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						frappe.msgprint({
							title: __('Duplicate Transport Job'),
							message: __('A Transport Job ({0}) already exists for Transport Order {1}. Please select a different Transport Order or use the existing Transport Job.', [
								r.message[0].name,
								frm.doc.transport_order
							]),
							indicator: 'red'
						});
						// Clear the transport_order field to prevent saving
						frm.set_value('transport_order', '');
					}
				}
			});
		}
		
		// Fetch scheduled_date from Transport Order when transport_order is set
		if (frm.doc.transport_order && !frm.doc.scheduled_date) {
			frm.events.fetch_scheduled_date_from_transport_order(frm);
		}
	},

	status: function(frm) {
		// Handle status changes, particularly when status changes to "In Progress" or "Completed"
		// Status changes to "In Progress" are triggered when:
		// - A transport leg card is started from Run Sheet (via startTransportLeg() function)
		// - This triggers: Run Sheet -> Transport Leg start_date set -> Transport Leg after_save() 
		//   -> update_transport_job_status() -> Transport Job status = "In Progress"
		const current_status = frm.doc.status;
		const previous_status = frm._previous_status || null;
		
		// Store current status for next change detection
		frm._previous_status = current_status;
		
		// When status changes to "In Progress"
		if (current_status === 'In Progress' && previous_status !== 'In Progress') {
			frm.events.on_status_in_progress(frm, previous_status);
		}
		
		// When status changes to "Completed"
		if (current_status === 'Completed' && previous_status !== 'Completed') {
			frm.events.on_status_completed(frm, previous_status);
		}
	},

	on_status_in_progress: function(frm, previous_status) {
		// Handle actions when status changes to "In Progress"
		// This is called when the status field changes to "In Progress"
		// This typically happens when a transport leg card is started from Run Sheet
		
		// Show notification that job is now in progress
		if (previous_status && previous_status !== 'In Progress') {
			frappe.show_alert({
				message: __('Transport Job is now In Progress - A transport leg card has been started from Run Sheet'),
				indicator: 'blue'
			}, 5);
		}
		
		// Refresh the legs field to ensure all leg data is up-to-date
		// Status changes to "In Progress" happen when:
		// - A transport leg card is started from Run Sheet (leg start_date is set, leg status becomes "Started")
		// - A leg is assigned to a run sheet (leg status becomes "Assigned")
		frm.refresh_field('legs');
		
		// You can add additional actions here, such as:
		// - Updating UI indicators
		// - Triggering notifications
		// - Fetching related data
		// - Logging the status change
		// - Refreshing related child tables or fields
	},
	
	create_sales_invoice_manual: function(frm) {
		// Manual creation of Sales Invoice from Actions menu
		// Check if Sales Invoice already exists
		if (frm.doc.sales_invoice) {
			frappe.show_alert({
				message: __('Sales Invoice {0} already exists for this Transport Job', [frm.doc.sales_invoice]),
				indicator: 'blue'
			}, 5);
			return;
		}
		
		// Check if Transport Job status is "Completed"
		if (frm.doc.status !== 'Completed') {
			frappe.msgprint({
				title: __('Cannot Create Sales Invoice'),
				message: __('Sales Invoice can only be created when Transport Job status is "Completed". Current status: {0}', [frm.doc.status || 'Draft']),
				indicator: 'red'
			});
			return;
		}
		
		// Call the shared function to create Sales Invoice
		frm.events.create_sales_invoice_call(frm, true);
	},
	
	create_sales_invoice_call: function(frm, open_invoice) {
		// Shared function to create Sales Invoice
		// open_invoice: if true, navigate to the created invoice
		frappe.call({
			method: 'logistics.transport.doctype.transport_job.transport_job.create_sales_invoice',
			args: {
				job_name: frm.doc.name
			},
			freeze: true,
			freeze_message: __('Creating Sales Invoice...'),
			callback: function(r) {
				try {
					if (!r || !r.message) {
						frappe.show_alert({
							message: __('Error: Invalid response from server'),
							indicator: 'red'
						}, 5);
						return;
					}
					
					if (r.message.ok && r.message.sales_invoice) {
						frappe.show_alert({
							message: __('Sales Invoice {0} created successfully', [r.message.sales_invoice]),
							indicator: 'green'
						}, 5);
						
						// Reload the document to get the updated sales_invoice field
						// The backend already updates the field via db.set_value
						frm.reload_doc().then(function() {
							// Optionally open the Sales Invoice after reload
							if (open_invoice && r.message.sales_invoice) {
								frappe.set_route('Form', 'Sales Invoice', r.message.sales_invoice);
							}
						});
					} else {
						frappe.show_alert({
							message: __('Error creating Sales Invoice: {0}', [r.message.message || 'Unknown error']),
							indicator: 'red'
						}, 5);
					}
				} catch (e) {
					console.error('Error handling Sales Invoice creation response:', e);
					frappe.show_alert({
						message: __('Error processing response: {0}', [e.message || 'Unknown error']),
						indicator: 'red'
					}, 5);
				}
			},
			error: function(r) {
				try {
					// Check if error is because Sales Invoice already exists
					const error_msg = (r && r.message) ? (typeof r.message === 'string' ? r.message : r.message.message || '') : '';
					if (error_msg.includes('already exists')) {
						// Extract Sales Invoice name from error message if possible
						const match = error_msg.match(/Sales Invoice\s+([A-Z0-9-]+)/i);
						if (match && match[1]) {
							frappe.show_alert({
								message: __('Sales Invoice {0} already exists for this Transport Job', [match[1]]),
								indicator: 'blue'
							}, 5);
							// Reload to get the existing sales_invoice value
							frm.reload_doc();
						} else {
							frappe.show_alert({
								message: __('Sales Invoice already exists for this Transport Job'),
								indicator: 'blue'
							}, 5);
							// Reload to get the existing sales_invoice value
							frm.reload_doc();
						}
					} else {
						frappe.show_alert({
							message: __('Error creating Sales Invoice: {0}', [error_msg || 'Unknown error']),
							indicator: 'red'
						}, 5);
					}
				} catch (e) {
					console.error('Error handling Sales Invoice creation error:', e);
					frappe.show_alert({
						message: __('Error: {0}', [e.message || 'Unknown error']),
						indicator: 'red'
					}, 5);
				}
			}
		});
	},
	
	on_status_completed: function(frm, previous_status) {
		// Handle actions when status changes to "Completed"
		// This is called when the status field changes to "Completed"
		// This typically happens when all transport legs are completed
		
		// Show notification that job is now completed
		if (previous_status && previous_status !== 'Completed') {
			frappe.show_alert({
				message: __('Transport Job is now Completed'),
				indicator: 'green'
			}, 5);
		}
		
		// Check if Sales Invoice already exists
		if (frm.doc.sales_invoice) {
			frappe.show_alert({
				message: __('Sales Invoice {0} already exists for this Transport Job', [frm.doc.sales_invoice]),
				indicator: 'blue'
			}, 5);
			return;
		}
		
		// Create Sales Invoice automatically when status becomes "Completed"
		// open_invoice = true to automatically navigate to the created invoice
		frm.events.create_sales_invoice_call(frm, true);
		
		// Refresh the legs field to ensure all leg data is up-to-date
		frm.refresh_field('legs');
	},
	
	status_check_cleanup: function(frm) {
		// Clean up realtime event listener when form is closed
		if (frm._status_realtime_listener) {
			frappe.realtime.off('transport_job_status_changed', frm._status_realtime_listener);
			frm._status_realtime_listener = null;
		}
	},

	toggle_container_fields: function(frm) {
		// Show/hide container fields based on transport_job_type
		const is_container = frm.doc.transport_job_type === 'Container';
		
		frm.set_df_property('container_type', 'hidden', !is_container);
		frm.set_df_property('container_no', 'hidden', !is_container);
		
		// Clear container fields if not Container
		if (!is_container) {
			if (frm.doc.container_type) {
				frm.set_value('container_type', null);
			}
			if (frm.doc.container_no) {
				frm.set_value('container_no', null);
			}
		}
	},

	toggle_consolidate_visibility: function(frm) {
		// Hide consolidate checkbox when transport_job_type is Container
		const is_container = frm.doc.transport_job_type === 'Container';
		frm.set_df_property('consolidate', 'hidden', is_container);
		
		// Clear consolidate value if Container
		if (is_container && frm.doc.consolidate) {
			frm.set_value('consolidate', 0);
		}
	},

	toggle_vehicle_type_required: function(frm) {
		// Vehicle Type is mandatory only if Consolidate checkbox is not checked
		const is_required = !frm.doc.consolidate;
		frm.set_df_property('vehicle_type', 'reqd', is_required);
	},


	validate: function(frm) {
		// Ensure transport_job_type is set before save
		if (!frm.doc.transport_job_type) {
			frm.set_value('transport_job_type', 'Non-Container');
		}
		if (!frm.doc.transport_job_type) {
			frappe.throw(__('Transport Job Type is required. Please select a Transport Job Type before saving.'));
		}
		
		// Validate vehicle_type is required only if consolidate is not checked
		if (!frm.doc.vehicle_type && !frm.doc.consolidate) {
			frappe.throw(__('Vehicle Type is required when Consolidate is not checked.'));
		}
		
		// Note: Duplicate prevention for transport_order is handled server-side in Python
		// The client-side check in transport_order field change event provides early feedback
		
		// Fetch and update missing data from Transport Leg before save
		frm.events.update_legs_missing_data(frm);
	},
	
	on_submit: function(frm) {
		// Refresh status field after submission to show updated status
		// The Python after_submit() hook updates the status via db_set()
		// Frappe automatically reloads after submit, but we need to ensure status is refreshed
		// Use a retry mechanism to ensure Python after_submit completes and status is updated
		let retry_count = 0;
		const max_retries = 10;
		const retry_delay = 400;
		
		const fetch_and_update_status = function() {
			// Fetch the latest status directly from database (bypassing form cache)
			frappe.db.get_value('Transport Job', frm.doc.name, ['status', 'docstatus', 'sales_invoice'], (r) => {
				if (r && r.docstatus === 1) {
					const db_status = r.status || 'Draft';
					const previous_status = frm.doc.status;
					
					// Update the document's status value directly (status field is not read-only)
					if (r.status && r.status !== frm.doc.status) {
						frm.doc.status = r.status;
						// Trigger status change handler if status changed to "In Progress"
						if (r.status === 'In Progress' && previous_status !== 'In Progress') {
							frm.events.on_status_in_progress(frm, previous_status);
						}
						// Trigger status change handler if status changed to "Completed"
						if (r.status === 'Completed' && previous_status !== 'Completed') {
							// Update sales_invoice field if available
							if (r.sales_invoice) {
								frm.doc.sales_invoice = r.sales_invoice;
							}
							frm.events.on_status_completed(frm, previous_status);
						}
						// Refresh the status field to ensure UI reflects current value
						frm.refresh_field('status');
					}
					// Update sales_invoice field if it changed
					if (r.sales_invoice !== undefined && r.sales_invoice !== frm.doc.sales_invoice) {
						frm.doc.sales_invoice = r.sales_invoice;
						frm.refresh_field('sales_invoice');
					}
					// Update docstatus if needed
					if (r.docstatus !== undefined && r.docstatus !== frm.doc.docstatus) {
						frm.doc.docstatus = r.docstatus;
					}
					// Update previous status tracking
					frm._previous_status = r.status || frm.doc.status;
					
					// If status is still Draft for a submitted document, retry
					// This handles cases where Python after_submit hasn't completed yet
					if (db_status === 'Draft' && retry_count < max_retries) {
						retry_count++;
						setTimeout(fetch_and_update_status, retry_delay);
					} else if (db_status !== 'Draft') {
						// Status was updated successfully, ensure UI is refreshed
						frm.refresh_field('status');
					}
				} else if (retry_count < max_retries) {
					// If we didn't get a valid response or docstatus is not 1 yet, retry
					retry_count++;
					setTimeout(fetch_and_update_status, retry_delay);
				}
			});
		};
		
		// Start fetching status after a delay to allow Python after_submit to complete
		// Python after_submit runs synchronously, but db_set might take a moment to commit
		setTimeout(function() {
			// First, reload the document to get the latest data from server
			frm.reload_doc().then(function() {
				// Then check and update status with retry mechanism
				fetch_and_update_status();
			}).catch(function() {
				// If reload fails, still try to fetch status directly
				fetch_and_update_status();
			});
		}, 800);
	},
	
	on_cancel: function(frm) {
		// Set status to Cancelled immediately when document is cancelled
		// The Python on_cancel hook will also set it, but we update UI immediately
		frm.doc.status = 'Cancelled';
		frm.refresh_field('status');
		
		// Reload the document to get the latest status from server after Python on_cancel runs
		setTimeout(function() {
			frm.reload_doc().then(function() {
				// Fetch the latest status from database to ensure it's set correctly
				frappe.db.get_value('Transport Job', frm.doc.name, ['status', 'docstatus'], (r) => {
					if (r) {
						if (r.status) {
							frm.doc.status = r.status;
						}
						if (r.docstatus !== undefined) {
							frm.doc.docstatus = r.docstatus;
						}
						frm.refresh_field('status');
					}
				});
			});
		}, 500);
	},
	
	update_legs_missing_data: function(frm) {
		// Fetch and update missing data from Transport Leg for all legs
		// Only works for draft documents (docstatus = 0)
		if (frm.doc.docstatus !== 0) {
			return;
		}
		
		const legs = frm.doc.legs || [];
		
		// Check for duplicate transport_leg values
		const transport_leg_counts = {};
		legs.forEach((leg) => {
			if (leg.transport_leg) {
				transport_leg_counts[leg.transport_leg] = (transport_leg_counts[leg.transport_leg] || 0) + 1;
			}
		});
		
		// Determine if there are any duplicates
		const has_duplicates = Object.values(transport_leg_counts).some(count => count > 1);
		
		legs.forEach((leg, idx) => {
			if (!leg.transport_leg) {
				// Skip if transport_leg is not set
				return;
			}
			
			// Check if this transport_leg is a duplicate
			const is_duplicate = transport_leg_counts[leg.transport_leg] > 1;
			
			// Check if any required fields are missing
			const required_fields = [
				'facility_type_from', 'facility_from', 'facility_type_to', 'facility_to',
				'pick_mode', 'drop_mode', 'pick_address', 'drop_address', 'run_sheet'
			];
			
			const has_missing = required_fields.some(field => !leg[field]);
			
			if (has_missing) {
				// Fetch data from Transport Leg and update missing fields
				frappe.model.get_value('Transport Leg', leg.transport_leg, 
					['facility_type_from', 'facility_from', 'facility_type_to', 'facility_to',
					 'pick_mode', 'drop_mode', 'pick_address', 'drop_address', 'run_sheet', 'date'],
					(r) => {
						if (r) {
							// Update only missing fields
							if (!leg.facility_type_from && r.facility_type_from) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_type_from', r.facility_type_from);
							}
							if (!leg.facility_from && r.facility_from) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_from', r.facility_from);
							}
							if (!leg.facility_type_to && r.facility_type_to) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_type_to', r.facility_type_to);
							}
							if (!leg.facility_to && r.facility_to) {
								frappe.model.set_value(leg.doctype, leg.name, 'facility_to', r.facility_to);
							}
							if (!leg.pick_mode && r.pick_mode) {
								frappe.model.set_value(leg.doctype, leg.name, 'pick_mode', r.pick_mode);
							}
							if (!leg.drop_mode && r.drop_mode) {
								frappe.model.set_value(leg.doctype, leg.name, 'drop_mode', r.drop_mode);
							}
							if (!leg.pick_address && r.pick_address) {
								frappe.model.set_value(leg.doctype, leg.name, 'pick_address', r.pick_address);
							}
							if (!leg.drop_address && r.drop_address) {
								frappe.model.set_value(leg.doctype, leg.name, 'drop_address', r.drop_address);
							}
							// Don't update run_sheet if there are duplicate transport_leg values
							if (!leg.run_sheet && r.run_sheet && !is_duplicate) {
								frappe.model.set_value(leg.doctype, leg.name, 'run_sheet', r.run_sheet);
							}
							if (!leg.scheduled_date && r.date) {
								frappe.model.set_value(leg.doctype, leg.name, 'scheduled_date', r.date);
							}
						}
					}
				);
			}
		});
	},
	
	fetch_missing_leg_data_server: function(frm) {
		// Call server method to fetch missing data (works for submitted documents too)
		frappe.call({
			method: 'logistics.transport.doctype.transport_job.transport_job.fetch_missing_leg_data',
			args: {
				job_name: frm.doc.name
			},
			freeze: true,
			freeze_message: __('Fetching missing leg data...'),
			callback: function(r) {
				if (r.message) {
					if (r.message.updated_count > 0) {
						frappe.show_alert({
							message: __('Updated {0} leg(s) with missing data', [r.message.updated_count]),
							indicator: 'green'
						});
						frm.reload_doc();
					} else {
						frappe.show_alert({
							message: __('No missing data found in legs'),
							indicator: 'blue'
						});
					}
				}
			}
		});
	},

	fetch_scheduled_date_from_transport_order: function(frm) {
		// Fetch scheduled_date from Transport Order
		if (!frm.doc.transport_order) {
			return;
		}
		
		frappe.db.get_value('Transport Order', frm.doc.transport_order, 'scheduled_date', (r) => {
			if (r && r.scheduled_date && !frm.doc.scheduled_date) {
				frm.set_value('scheduled_date', r.scheduled_date);
			}
		});
	},
	
	check_run_sheet_statuses: function(frm) {
		// Check run sheet statuses and update Transport Job status to "In Progress"
		// if any run sheet has status "Dispatched", "In-Progress", or "Hold"
		if (!frm.doc.legs || frm.doc.legs.length === 0) {
			return;
		}
		
		// Get all unique run_sheet values from legs
		const run_sheets = new Set();
		frm.doc.legs.forEach((leg) => {
			if (leg.run_sheet) {
				run_sheets.add(leg.run_sheet);
			}
		});
		
		if (run_sheets.size === 0) {
			return; // No run sheets found
		}
		
		// Check status of each run sheet
		const run_sheet_names = Array.from(run_sheets);
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Run Sheet',
				filters: {
					name: ['in', run_sheet_names]
				},
				fields: ['name', 'status', 'docstatus'],
				limit: 100
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					// Check if any run sheet has status "Dispatched", "In-Progress", or "Hold"
					const in_progress_statuses = ['Dispatched', 'In-Progress', 'Hold'];
					const has_in_progress_run_sheet = r.message.some((rs) => {
						// Only check submitted run sheets (docstatus = 1)
						return rs.docstatus === 1 && in_progress_statuses.includes(rs.status);
					});
					
					if (has_in_progress_run_sheet && frm.doc.status !== 'In Progress') {
						// Update Transport Job status to "In Progress"
						// Only update if current status is not already "In Progress" or "Completed"
						// Don't override "Completed" status
						if (frm.doc.status !== 'Completed' && frm.doc.status !== 'Cancelled') {
							frappe.call({
								method: 'frappe.client.set_value',
								args: {
									doctype: 'Transport Job',
									name: frm.doc.name,
									fieldname: 'status',
									value: 'In Progress'
								},
								callback: function(update_r) {
									if (update_r.message) {
										frm.doc.status = 'In Progress';
										frm.refresh_field('status');
										// Update previous status tracking
										frm._previous_status = 'In Progress';
									}
								},
								error: function(update_r) {
									// Silently fail - don't show error to user
								}
							});
						}
					}
				}
			},
			error: function(r) {
				// Silently fail - don't show error to user
			}
		});
	},

	create_run_sheet: function(frm) {
		// Create Run Sheet(s) from Transport Job
		if (!frm.doc.name) {
			frappe.msgprint({
				title: __('Error'),
				message: __('Please save the Transport Job first.'),
				indicator: 'red'
			});
			return;
		}

		if (frm.doc.docstatus !== 1) {
			frappe.msgprint({
				title: __('Error'),
				message: __('Please submit the Transport Job first before creating a Run Sheet.'),
				indicator: 'red'
			});
			return;
		}

		frappe.call({
			method: 'logistics.transport.doctype.transport_job.transport_job.action_create_run_sheet',
			args: {
				jobname: frm.doc.name
			},
			freeze: true,
			freeze_message: __('Creating Run Sheet...'),
			callback: function(r) {
				if (r.message) {
					const result = r.message;
					if (result.run_sheets_created > 0) {
						let message = '';
						if (result.run_sheets_created === 1) {
							message = __('Run Sheet {0} created successfully with {1} leg(s)', [
								result.name,
								result.legs_added
							]);
							// Open the created Run Sheet
							if (result.name) {
								frappe.set_route('Form', 'Run Sheet', result.name);
							}
						} else {
							message = __('{0} Run Sheet(s) created successfully with {1} leg(s) total', [
								result.run_sheets_created,
								result.legs_added
							]);
							// Open the first Run Sheet if multiple were created
							if (result.names && result.names.length > 0) {
								frappe.set_route('Form', 'Run Sheet', result.names[0]);
							}
						}
						frappe.show_alert({
							message: message,
							indicator: 'green'
						});
						// Update run_sheet in legs child table from Transport Leg
						// This ensures the run_sheet field is populated even for submitted documents
						frappe.call({
							method: "logistics.transport.doctype.transport_job.transport_job.update_run_sheet_from_transport_leg",
							args: {
								job_name: frm.doc.name
							},
							callback: function(update_r) {
								// Reload the form to show any updated fields
								frm.reload_doc();
							},
							error: function(r) {
								// Even if update fails, reload the form
								frm.reload_doc();
							}
						});
					} else {
						frappe.show_alert({
							message: __('No Run Sheets were created. Please check if legs are available.'),
							indicator: 'orange'
						});
					}
				}
			},
			error: function(r) {
				frappe.show_alert({
					message: __('Error creating Run Sheet: {0}', [r.message || 'Unknown error']),
					indicator: 'red'
				});
			}
		});
	}
});

// Child table event handlers for Transport Job Legs
frappe.ui.form.on('Transport Job Legs', {
	transport_leg: function(frm, cdt, cdn) {
		// When transport_leg is selected, trigger a refresh to fetch data
		const row = locals[cdt][cdn];
		if (row.transport_leg) {
			frappe.model.set_value(cdt, cdn, 'transport_leg', row.transport_leg);
			frm.refresh_field('legs');
		}
	}
});
