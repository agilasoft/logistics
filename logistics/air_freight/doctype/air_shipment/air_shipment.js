// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Suppress "Air Shipment X not found" when form is new/unsaved (e.g. child grid triggers API before save)
frappe.ui.form.on("Air Shipment", {
	onload(frm) {
		if (frm.is_new() || frm.doc.__islocal) {
			if (!frappe._original_msgprint_as) {
				frappe._original_msgprint_as = frappe.msgprint;
			}
			frappe.msgprint = function(options) {
				const message = typeof options === 'string' ? options : (options && options.message || '');
				if (message && typeof message === 'string' &&
					message.includes('Air Shipment') &&
					message.includes('not found')) {
					return;
				}
				return frappe._original_msgprint_as.apply(this, arguments);
			};
			frm.$wrapper.one('form-refresh', function() {
				if (!frm.is_new() && !frm.doc.__islocal && frappe._original_msgprint_as) {
					frappe.msgprint = frappe._original_msgprint_as;
				}
			});
		}
		// Apply settings defaults when creating new document
		if (frm.is_new()) {
			apply_settings_defaults(frm);
		}
	},
	override_volume_weight: function(frm) {
		// Only call server when doc is saved to avoid "Air Shipment not found"
		if (!frm.doc.override_volume_weight && !frm.doc.__islocal) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message && r.message.volume !== undefined) {
						frm.set_value('volume', r.message.volume);
					}
				}
			});
		}
	},
	refresh(frm) {
		// Add button to load charges from Sales Quote
		if (frm.doc.sales_quote && !frm.is_new()) {
			frm.add_custom_button(__('Load Charges from Sales Quote'), function() {
				load_charges_from_sales_quote(frm);
			}, __('Pricing'));
		}
		
		// Add button to recalculate all charges
		if (frm.doc.charges && frm.doc.charges.length > 0 && !frm.is_new()) {
			frm.add_custom_button(__('Recalculate All Charges'), function() {
				recalculate_all_charges(frm);
			}, __('Pricing'));
		}
		
		// Add button to calculate total charges
		if (frm.doc.charges && frm.doc.charges.length > 0 && !frm.is_new()) {
			frm.add_custom_button(__('Calculate Total Charges'), function() {
				calculate_total_charges(frm);
			}, __('Pricing'));
		}

		// Create Transport Order / Inbound Order from Air Shipment
		if (!frm.is_new()) {
			frm.add_custom_button(__('Transport Order'), function() {
				frappe.call({
					method: 'logistics.utils.module_integration.create_transport_order_from_air_shipment',
					args: { air_shipment_name: frm.doc.name },
					callback: function(r) {
						if (r.exc) return;
						if (r.message && r.message.transport_order) {
							frappe.msgprint(r.message.message);
							setTimeout(function() {
								frappe.set_route('Form', 'Transport Order', r.message.transport_order);
							}, 100);
						}
					}
				});
			}, __('Create'));
			frm.add_custom_button(__('Inbound Order'), function() {
				frappe.call({
					method: 'logistics.utils.module_integration.create_inbound_order_from_air_shipment',
					args: { air_shipment_name: frm.doc.name },
					callback: function(r) {
						if (r.exc) return;
						if (r.message && r.message.inbound_order) {
							frappe.msgprint(r.message.message);
							setTimeout(function() {
								frappe.set_route('Form', 'Inbound Order', r.message.inbound_order);
							}, 100);
						}
					}
				});
			}, __('Create'));
		}

		// Additional Charges: Get Additional Charges and Create Change Request
		if (!frm.is_new()) {
			frm.add_custom_button(__('Get Additional Charges'), function() {
				logistics_additional_charges_show_sales_quote_dialog(frm, 'Air Shipment');
			}, __('Actions'));
			frm.add_custom_button(__('Create Change Request'), function() {
				frappe.call({
					method: 'logistics.pricing_center.doctype.change_request.change_request.create_change_request',
					args: { job_type: 'Air Shipment', job_name: frm.doc.name },
					callback: function(r) {
						if (r.message) frappe.set_route('Form', 'Change Request', r.message);
					}
				});
			}, __('Actions'));
		}
		console.log("Air Shipment form refreshed");
		console.log("Origin Port:", frm.doc.origin_port);
		console.log("Destination Port:", frm.doc.destination_port);
		
		// Apply settings defaults if document is new and not already applied
		if (frm.is_new() && !frm.doc._settings_applied) {
			apply_settings_defaults(frm);
		}
		
		// Update DG compliance status on form load (only when doc is saved to avoid "Air Shipment not found")
		if (!frm.is_new() && frm.doc.contains_dangerous_goods) {
			frm.call('refresh_dg_compliance_status').then(r => {
				if (r.message) {
					console.log("DG Compliance Status updated:", r.message.status);
					// Refresh milestone view to update badge
					refresh_milestone_view(frm);
				}
			}).catch(err => {
				console.error("Error refreshing DG compliance status:", err);
			});
		}
		
		// Check for dangerous goods and show alert only if non-compliant (only when doc is saved)
		if (!frm.is_new()) {
			frm.call('get_dg_dashboard_info').then(r => {
				if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
					show_dg_alert(frm, r.message);
				}
			}).catch(err => {
				console.error("Error getting DG dashboard info:", err);
			});
		}
		
		// Add DG compliance check button
		let contains_dg = frm.doc.contains_dangerous_goods || false;
		if (contains_dg || frm.doc.packages) {
			// Check if any package has dangerous goods
			let has_dg = false;
			if (frm.doc.packages) {
				for (let package of frm.doc.packages) {
					if (package.dg_substance || package.un_number || package.proper_shipping_name || package.dg_class) {
						has_dg = true;
						break;
					}
				}
			}
			
			if (has_dg || contains_dg) {
				frm.add_custom_button(__('Check DG Compliance'), function() {
				frm.call('check_dg_compliance').then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('DG Compliance Check'),
							message: r.message.message,
							indicator: r.message.status === 'Compliant' ? 'green' : 'red'
						});
					}
				});
			}, __('Dangerous Goods'));
			
			frm.add_custom_button(__('Generate DG Declaration'), function() {
				frm.call('generate_dg_declaration').then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('DG Declaration'),
							message: r.message.message,
							indicator: 'green'
						});
						frm.reload_doc();
					}
				});
			}, __('Dangerous Goods'));
			
			frm.add_custom_button(__('Send DG Alert'), function() {
				frm.call('send_dg_alert', {alert_type: 'compliance'}).then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('DG Alert'),
							message: r.message.message,
							indicator: 'blue'
						});
					}
				});
			}, __('Dangerous Goods'));
			}
		}
		
		// Only call if not already called recently
		if (!frm._milestone_html_called) {
			frm._milestone_html_called = true;
			console.log("Calling get_milestone_html...");
			frm.call('get_milestone_html').then(r => {
				console.log("Response from get_milestone_html:", r);
				console.log("Message content:", r.message);
				if (r.message) {
					const html = r.message || '';
					
					// Get the HTML field wrapper and set content directly
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(html);
						console.log("HTML set directly in DOM (virtual field)");
					}
					
					// Don't set the field value since it's virtual - just update DOM
					console.log("Milestone HTML rendered successfully");
				} else {
					console.log("No message in response");
				}
			}).catch(err => {
				console.error("Error calling get_milestone_html:", err);
			});
			
			// Reset flag after 2 seconds
			setTimeout(() => {
				frm._milestone_html_called = false;
			}, 2000);
		}
		
		// Populate display fields if they are empty but link fields have values
		populate_display_fields_if_missing(frm);
	},
	
	origin_port(frm) {
		console.log("Origin port changed to:", frm.doc.origin_port);
		// Regenerate milestone HTML when origin port changes
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.call('get_milestone_html').then(r => {
				if (r.message) {
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(r.message);
					}
				}
			});
		}
	},
	
	destination_port(frm) {
		console.log("Destination port changed to:", frm.doc.destination_port);
		// Regenerate milestone HTML when destination port changes
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.call('get_milestone_html').then(r => {
				if (r.message) {
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(r.message);
					}
				}
			});
		}
	},
	
	contains_dangerous_goods(frm) {
		// Refresh DG alert when dangerous goods flag changes
		let contains_dg = frm.doc.contains_dangerous_goods || false;
		if (contains_dg) {
			// Update DG compliance status
			frm.call('refresh_dg_compliance_status').then(r => {
				if (r.message) {
					console.log("DG Compliance Status updated:", r.message.status);
				}
			});
			
			frm.call('get_dg_dashboard_info').then(r => {
				if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
					show_dg_alert(frm, r.message);
				} else {
					// Remove alert if compliant
					remove_dg_alert(frm);
				}
			}).catch(err => {
				console.error("Error getting DG dashboard info:", err);
			});
		} else {
			// Remove DG alert if unchecked
			remove_dg_alert(frm);
		}
		
		// Refresh milestone view to update DG compliance badge
		refresh_milestone_view(frm);
	},
	
	dg_compliance_status(frm) {
		// Refresh milestone view when DG compliance status changes
		refresh_milestone_view(frm);
	},
	
	dg_declaration_complete(frm) {
		// Update DG compliance status when declaration completion changes
		frm.call('refresh_dg_compliance_status').then(r => {
			if (r.message) {
				console.log("DG Compliance Status updated:", r.message.status);
			}
		});
		
		// Check if alert should be shown or removed based on new compliance status
		frm.call('get_dg_dashboard_info').then(r => {
			if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
				show_dg_alert(frm, r.message);
			} else {
				// Remove alert if compliant
				remove_dg_alert(frm);
			}
		}).catch(err => {
			console.error("Error getting DG dashboard info:", err);
		});
		
		// Refresh milestone view when DG declaration completion changes
		refresh_milestone_view(frm);
	},
	
	// Handler for shipper address - populate display field
	shipper_address(frm) {
		if (frm.doc.shipper_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					address_dict: frm.doc.shipper_address
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('shipper_address_display', r.message);
					} else {
						frm.set_value('shipper_address_display', '');
					}
				}
			});
		} else {
			frm.set_value('shipper_address_display', '');
		}
	},
	
	// Handler for consignee address - populate display field
	consignee_address(frm) {
		if (frm.doc.consignee_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: {
					address_dict: frm.doc.consignee_address
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('consignee_address_display', r.message);
					} else {
						frm.set_value('consignee_address_display', '');
					}
				}
			});
		} else {
			frm.set_value('consignee_address_display', '');
		}
	},
	
	// Handler for shipper contact - populate display field
	shipper_contact(frm) {
		if (frm.doc.shipper_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Contact',
					name: frm.doc.shipper_contact
				},
				callback: function(r) {
					if (r.message) {
						const contact = r.message;
						let display_text = '';
						
						// Build contact display text
						if (contact.first_name || contact.last_name) {
							display_text = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
						} else if (contact.name) {
							display_text = contact.name;
						}
						
						if (contact.designation) {
							display_text += display_text ? '\n' + contact.designation : contact.designation;
						}
						
						if (contact.phone) {
							display_text += display_text ? '\n' + contact.phone : contact.phone;
						}
						
						if (contact.mobile_no) {
							display_text += display_text ? '\n' + contact.mobile_no : contact.mobile_no;
						}
						
						if (contact.email_id) {
							display_text += display_text ? '\n' + contact.email_id : contact.email_id;
						}
						
						frm.set_value('shipper_contact_display', display_text);
					} else {
						frm.set_value('shipper_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('shipper_contact_display', '');
		}
	},
	
	// Handler for consignee contact - populate display field
	consignee_contact(frm) {
		if (frm.doc.consignee_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Contact',
					name: frm.doc.consignee_contact
				},
				callback: function(r) {
					if (r.message) {
						const contact = r.message;
						let display_text = '';
						
						// Build contact display text
						if (contact.first_name || contact.last_name) {
							display_text = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
						} else if (contact.name) {
							display_text = contact.name;
						}
						
						if (contact.designation) {
							display_text += display_text ? '\n' + contact.designation : contact.designation;
						}
						
						if (contact.phone) {
							display_text += display_text ? '\n' + contact.phone : contact.phone;
						}
						
						if (contact.mobile_no) {
							display_text += display_text ? '\n' + contact.mobile_no : contact.mobile_no;
						}
						
						if (contact.email_id) {
							display_text += display_text ? '\n' + contact.email_id : contact.email_id;
						}
						
						frm.set_value('consignee_contact_display', display_text);
					} else {
						frm.set_value('consignee_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('consignee_contact_display', '');
		}
	}
});

// Function to show dangerous goods alert in header (only for non-compliant status)
function show_dg_alert(frm, dg_info) {
	// Remove existing alert if any
	remove_dg_alert(frm);
	
	// Only show alert for non-compliant status
	if (dg_info.compliance_status !== 'Non-Compliant') {
		return;
	}
	
	// Set alert styling for non-compliant status
	let alert_level = 'danger';
	let alert_icon = 'fa-exclamation-triangle';
	let alert_text = '⚠️ DANGEROUS GOODS NON-COMPLIANT ⚠️';
	
	// Create alert element
	const alert_html = `
		<div id="dg-alert-banner" class="dg-alert-banner alert-${alert_level}" style="
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			z-index: 1050;
			padding: 10px 20px;
			margin: 0;
			border-radius: 0;
			font-weight: bold;
			text-align: center;
			box-shadow: 0 2px 4px rgba(0,0,0,0.2);
			animation: slideDown 0.3s ease-out;
		">
			<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
				<i class="fa ${alert_icon}" style="font-size: 18px;"></i>
				<span>${alert_text}</span>
				<i class="fa ${alert_icon}" style="font-size: 18px;"></i>
			</div>
			<div style="font-size: 14px; margin-top: 5px; opacity: 0.9;">
				${dg_info.message}
				${dg_info.emergency_contact ? ` | Emergency: ${dg_info.emergency_contact} (${dg_info.emergency_phone})` : ''}
				${dg_info.compliance_status ? ` | Status: ${dg_info.compliance_status}` : ''}
			</div>
			<div style="position: absolute; top: 5px; right: 10px;">
				<button type="button" class="btn btn-sm" onclick="remove_dg_alert()" style="
					background: rgba(255,255,255,0.2);
					border: 1px solid rgba(255,255,255,0.3);
					color: white;
					padding: 2px 8px;
					border-radius: 3px;
				">
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>
		
		<style>
		@keyframes slideDown {
			from { transform: translateY(-100%); }
			to { transform: translateY(0); }
		}
		
		.dg-alert-banner.alert-danger {
			background: linear-gradient(135deg, #dc3545, #c82333);
			color: white;
			border-left: 5px solid #721c24;
		}
		
		.dg-alert-banner.alert-warning {
			background: linear-gradient(135deg, #ffc107, #e0a800);
			color: #212529;
			border-left: 5px solid #856404;
		}
		
		.dg-alert-banner.alert-info {
			background: linear-gradient(135deg, #17a2b8, #138496);
			color: white;
			border-left: 5px solid #0c5460;
		}
		
		/* Adjust body padding when alert is shown */
		body.dg-alert-shown {
			padding-top: 80px !important;
		}
		</style>
	`;
	
	// Add alert to page
	$('body').prepend(alert_html);
	$('body').addClass('dg-alert-shown');
	
	// Add click handler for close button
	window.remove_dg_alert = function() {
		remove_dg_alert(frm);
	};
}

// Function to remove dangerous goods alert
function remove_dg_alert(frm) {
	// Check if alert can be dismissed by looking for the lock icon
	const alert_banner = $('#dg-alert-banner');
	if (alert_banner.length && alert_banner.find('.fa-lock').length > 0) {
		// Alert is locked and cannot be dismissed
		frappe.msgprint({
			title: __('Alert Cannot Be Dismissed'),
			message: __('This dangerous goods alert cannot be dismissed until DG compliance is complete. Please ensure all required fields are filled and compliance status is "Compliant".'),
			indicator: 'red'
		});
		return;
	}
	
	$('#dg-alert-banner').remove();
	$('body').removeClass('dg-alert-shown');
	delete window.remove_dg_alert;
}

// Package table field change handlers
frappe.ui.form.on("Air Shipment Packages", {
	volume(frm) {
		// Skip server call when parent is unsaved to avoid "Air Shipment not found"
		if (frm.doc && !frm.doc.override_volume_weight && !frm.doc.__islocal) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
					}
				}
			});
		}
	},
	weight(frm) {
		// Skip server call when parent is unsaved to avoid "Air Shipment not found"
		if (frm.doc && !frm.doc.override_volume_weight && !frm.doc.__islocal) {
			frm.call({
				method: 'aggregate_volume_from_packages_api',
				doc: frm.doc,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.volume !== undefined) frm.set_value('volume', r.message.volume);
						if (r.message.weight !== undefined) frm.set_value('weight', r.message.weight);
					}
				}
			});
		}
	},
	length(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	width(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	height(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	dimension_uom(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },
	volume_uom(frm, cdt, cdn) { if (typeof logistics_calculate_volume_from_dimensions === 'function') logistics_calculate_volume_from_dimensions(frm, cdt, cdn); },

	dg_substance(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	un_number(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	proper_shipping_name(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	dg_class(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	is_radioactive(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	temp_controlled(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	emergency_contact_name(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	},
	emergency_contact_phone(frm, cdt, cdn) {
		check_and_update_dg_status(frm);
	}
});

// Function to check and update dangerous goods status
function check_and_update_dg_status(frm) {
	// Skip server calls when doc is unsaved (avoids "Air Shipment not found" from get_doc on server)
	const doc_saved = !frm.is_new() && !frm.doc.__islocal;

	// Check if any package has dangerous goods
	let has_dg = false;
	if (frm.doc.packages) {
		for (let package of frm.doc.packages) {
			if (package.dg_substance || package.un_number || package.proper_shipping_name || package.dg_class) {
				has_dg = true;
				break;
			}
		}
	}
	
	// Update the main dangerous goods flag
	let contains_dg = frm.doc.contains_dangerous_goods || false;
	if (has_dg && !contains_dg) {
		frm.set_value('contains_dangerous_goods', 1);
		if (doc_saved) {
			// Update DG compliance status
			frm.call('refresh_dg_compliance_status').then(r => {
				if (r.message) {
					console.log("DG Compliance Status updated:", r.message.status);
				}
			});
			// Trigger DG alert only if non-compliant
			setTimeout(() => {
				frm.call('get_dg_dashboard_info').then(r => {
					if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
						show_dg_alert(frm, r.message);
					} else {
						// Remove alert if compliant
						remove_dg_alert(frm);
					}
				});
			}, 500);
		}
	} else if (!has_dg && contains_dg) {
		frm.set_value('contains_dangerous_goods', 0);
		remove_dg_alert(frm);
	} else if (has_dg && contains_dg && doc_saved) {
		// Update DG compliance status for existing DG packages
		frm.call('refresh_dg_compliance_status').then(r => {
			if (r.message) {
				console.log("DG Compliance Status updated:", r.message.status);
			}
		});
		
		// Check if alert should be shown or removed based on compliance status
		frm.call('get_dg_dashboard_info').then(r => {
			if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
				show_dg_alert(frm, r.message);
			} else {
				// Remove alert if compliant
				remove_dg_alert(frm);
			}
		}).catch(err => {
			console.error("Error getting DG dashboard info:", err);
		});
	}
	
	// Refresh milestone view to update DG compliance badge (only when doc exists on server)
	if (doc_saved) {
		refresh_milestone_view(frm);
	}
}

// Function to populate display fields if they are missing but link fields have values
function populate_display_fields_if_missing(frm) {
	// Populate shipper address display if missing
	if (frm.doc.shipper_address && !frm.doc.shipper_address_display) {
		frappe.call({
			method: 'frappe.contacts.doctype.address.address.get_address_display',
			args: {
				address_dict: frm.doc.shipper_address
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('shipper_address_display', r.message);
				}
			}
		});
	}
	
	// Populate consignee address display if missing
	if (frm.doc.consignee_address && !frm.doc.consignee_address_display) {
		frappe.call({
			method: 'frappe.contacts.doctype.address.address.get_address_display',
			args: {
				address_dict: frm.doc.consignee_address
			},
			callback: function(r) {
				if (r.message) {
					frm.set_value('consignee_address_display', r.message);
				}
			}
		});
	}
	
	// Populate shipper contact display if missing
	if (frm.doc.shipper_contact && !frm.doc.shipper_contact_display) {
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Contact',
				name: frm.doc.shipper_contact
			},
			callback: function(r) {
				if (r.message) {
					const contact = r.message;
					let display_text = '';
					
					if (contact.first_name || contact.last_name) {
						display_text = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
					} else if (contact.name) {
						display_text = contact.name;
					}
					
					if (contact.designation) {
						display_text += display_text ? '\n' + contact.designation : contact.designation;
					}
					
					if (contact.phone) {
						display_text += display_text ? '\n' + contact.phone : contact.phone;
					}
					
					if (contact.mobile_no) {
						display_text += display_text ? '\n' + contact.mobile_no : contact.mobile_no;
					}
					
					if (contact.email_id) {
						display_text += display_text ? '\n' + contact.email_id : contact.email_id;
					}
					
					frm.set_value('shipper_contact_display', display_text);
				}
			}
		});
	}
	
	// Populate consignee contact display if missing
	if (frm.doc.consignee_contact && !frm.doc.consignee_contact_display) {
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Contact',
				name: frm.doc.consignee_contact
			},
			callback: function(r) {
				if (r.message) {
					const contact = r.message;
					let display_text = '';
					
					if (contact.first_name || contact.last_name) {
						display_text = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
					} else if (contact.name) {
						display_text = contact.name;
					}
					
					if (contact.designation) {
						display_text += display_text ? '\n' + contact.designation : contact.designation;
					}
					
					if (contact.phone) {
						display_text += display_text ? '\n' + contact.phone : contact.phone;
					}
					
					if (contact.mobile_no) {
						display_text += display_text ? '\n' + contact.mobile_no : contact.mobile_no;
					}
					
					if (contact.email_id) {
						display_text += display_text ? '\n' + contact.email_id : contact.email_id;
					}
					
					frm.set_value('consignee_contact_display', display_text);
				}
			}
		});
	}
}

// Function to refresh milestone view when DG compliance status changes
function refresh_milestone_view(frm) {
	// Check if milestone view is currently displayed
	if (frm.dashboard && frm.dashboard.wrapper && frm.dashboard.wrapper.find('.milestone-container').length > 0) {
		// Refresh the milestone HTML
		frm.call('get_milestone_html').then(r => {
			if (r.message) {
				// Update the milestone container with new HTML
				frm.dashboard.wrapper.find('.milestone-container').html(r.message);
			}
		}).catch(err => {
			console.error("Error refreshing milestone view:", err);
		});
	}
}

// Function to load charges from Sales Quote
function load_charges_from_sales_quote(frm) {
	if (!frm.doc.sales_quote) {
		frappe.msgprint({
			title: __("Error"),
			message: __("Sales Quote is not set for this Air Shipment."),
			indicator: "red"
		});
		return;
	}
	
	frappe.confirm(
		__("This will replace all existing charges with charges from Sales Quote. Do you want to continue?"),
		function() {
			// Show loading indicator
			frm.dashboard.set_headline_alert(__("Loading charges from Sales Quote..."));
			
			// Call the server method
			frm.call({
				method: "populate_charges_from_sales_quote",
				args: {
					docname: frm.doc.name
				},
				callback: function(r) {
					frm.dashboard.clear_headline();
					
					if (r.message && r.message.success) {
						// Refresh the form to show new charges
						frm.refresh_field("charges");
						
						frappe.msgprint({
							title: __("Charges Loaded"),
							message: __("Successfully loaded {0} charges from Sales Quote.", [r.message.charges_added]),
							indicator: "green"
						});
					} else {
						frappe.msgprint({
							title: __("Error"),
							message: r.message && r.message.message ? r.message.message : __("Failed to load charges from Sales Quote."),
							indicator: "red"
						});
					}
				},
				error: function(r) {
					frm.dashboard.clear_headline();
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to load charges from Sales Quote. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	);
}

// Function to recalculate all charges
function recalculate_all_charges(frm) {
	if (!frm.doc.charges || frm.doc.charges.length === 0) {
		frappe.msgprint({
			title: __("Error"),
			message: __("No charges found to recalculate."),
			indicator: "red"
		});
		return;
	}
	
	// Show loading indicator
	frm.dashboard.set_headline_alert(__("Recalculating charges..."));
	
	// Call the server method (doc required for run_doc_method)
	frm.call({
		doc: frm.doc,
		method: "recalculate_all_charges",
		callback: function(r) {
			frm.dashboard.clear_headline();
			
			if (r.message && r.message.success) {
				// Refresh the form to show updated charges
				frm.refresh_field("charges");
				
				frappe.msgprint({
					title: __("Charges Recalculated"),
					message: __("Successfully recalculated {0} charges.", [r.message.charges_recalculated]),
					indicator: "green"
				});
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: r.message && r.message.message ? r.message.message : __("Failed to recalculate charges."),
					indicator: "red"
				});
			}
		},
		error: function(r) {
			frm.dashboard.clear_headline();
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to recalculate charges. Please try again."),
				indicator: "red"
			});
		}
	});
}

// Function to calculate total charges
function calculate_total_charges(frm) {
	if (!frm.doc.charges || frm.doc.charges.length === 0) {
		frappe.msgprint({
			title: __("Error"),
			message: __("No charges found to calculate."),
			indicator: "red"
		});
		return;
	}
	
	// Call the server method (doc required for run_doc_method)
	frm.call({
		doc: frm.doc,
		method: "calculate_total_charges",
		callback: function(r) {
			if (r.message) {
				const total = r.message.total_charges || 0;
				const currency = r.message.currency || "";
				
				frappe.msgprint({
					title: __("Total Charges"),
					message: __("Total Charges: {0} {1}", [currency, total.toFixed(2)]),
					indicator: "blue"
				});
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to calculate total charges. Please try again."),
				indicator: "red"
			});
		}
	});
}

// Calculate charge amount when rate or quantity changes
frappe.ui.form.on("Air Shipment Charges", {
	rate: function(frm, cdt, cdn) {
		calculate_charge_amount(frm, cdt, cdn);
	},
	quantity: function(frm, cdt, cdn) {
		calculate_charge_amount(frm, cdt, cdn);
	},
	charge_basis: function(frm, cdt, cdn) {
		calculate_charge_amount(frm, cdt, cdn);
	},
	discount_percentage: function(frm, cdt, cdn) {
		calculate_charge_amount(frm, cdt, cdn);
	},
	surcharge_amount: function(frm, cdt, cdn) {
		calculate_charge_amount(frm, cdt, cdn);
	}
});

// Function to calculate charge amount
function calculate_charge_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row.rate || !row.charge_basis) {
		return;
	}
	
	let base_amount = 0;
	const rate = parseFloat(row.rate) || 0;
	const quantity = parseFloat(row.quantity) || 0;
	
	// Calculate base amount based on charge basis
	if (row.charge_basis === "Per kg" || row.charge_basis === "Per m³" || row.charge_basis === "Per package") {
		base_amount = rate * quantity;
	} else if (row.charge_basis === "Per shipment" || row.charge_basis === "Fixed amount") {
		base_amount = rate;
	} else if (row.charge_basis === "Percentage") {
		// For percentage, use chargeable weight from parent
		const chargeable = parseFloat(frm.doc.chargeable) || parseFloat(frm.doc.weight) || 0;
		base_amount = rate * (chargeable * 0.01);
	}
	
	// Calculate discount
	const discount_percentage = parseFloat(row.discount_percentage) || 0;
	const discount_amount = base_amount * (discount_percentage / 100);
	
	// Calculate surcharge
	const surcharge_amount = parseFloat(row.surcharge_amount) || 0;
	
	// Calculate tax (if applicable)
	const tax_amount = parseFloat(row.tax_amount) || 0;
	
	// Calculate total
	const total_amount = base_amount - discount_amount + surcharge_amount + tax_amount;
	
	// Update fields
	frappe.model.set_value(cdt, cdn, {
		base_amount: base_amount,
		discount_amount: discount_amount,
		total_amount: Math.max(0, total_amount)
	});
	
	// Refresh the field
	frm.refresh_field("charges");
}

// Function to apply settings defaults
function apply_settings_defaults(frm) {
	if (frm.doc._settings_applied) {
		return;
	}
	
	// Get company
	const company = frm.doc.company || frappe.defaults.get_user_default("Company");
	if (!company) {
		return;
	}
	
	// Get Air Freight Settings
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Air Freight Settings",
			filters: {
				company: company
			},
			limit_page_length: 1
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				// Get the first settings document
				frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Air Freight Settings",
						name: r.message[0].name
					},
					callback: function(r2) {
						if (r2.message) {
							const settings = r2.message;
							
							// Apply general settings
							if (!frm.doc.branch && settings.default_branch) {
								frm.set_value("branch", settings.default_branch);
							}
							if (!frm.doc.cost_center && settings.default_cost_center) {
								frm.set_value("cost_center", settings.default_cost_center);
							}
							if (!frm.doc.profit_center && settings.default_profit_center) {
								frm.set_value("profit_center", settings.default_profit_center);
							}
							if (!frm.doc.incoterm && settings.default_incoterm) {
								frm.set_value("incoterm", settings.default_incoterm);
							}
							if (!frm.doc.service_level && settings.default_service_level) {
								frm.set_value("service_level", settings.default_service_level);
							}
							
							// Apply location settings
							if (!frm.doc.origin_port && settings.default_origin_port) {
								frm.set_value("origin_port", settings.default_origin_port);
							}
							if (!frm.doc.destination_port && settings.default_destination_port) {
								frm.set_value("destination_port", settings.default_destination_port);
							}
							
							// Apply business settings
							if (!frm.doc.airline && settings.default_airline) {
								frm.set_value("airline", settings.default_airline);
							}
							if (!frm.doc.freight_agent && settings.default_freight_agent) {
								frm.set_value("freight_agent", settings.default_freight_agent);
							}
							if (!frm.doc.house_type && settings.default_house_type) {
								frm.set_value("house_type", settings.default_house_type);
							}
							if (!frm.doc.direction && settings.default_direction) {
								frm.set_value("direction", settings.default_direction);
							}
							if (!frm.doc.release_type && settings.default_release_type) {
								frm.set_value("release_type", settings.default_release_type);
							}
							if (!frm.doc.entry_type && settings.default_entry_type) {
								frm.set_value("entry_type", settings.default_entry_type);
							}
							
							// Apply document settings
							if (!frm.doc.uld_type && settings.default_uld_type) {
								frm.set_value("uld_type", settings.default_uld_type);
							}
							
							// Mark as applied
							frm.set_value("_settings_applied", 1);
						}
					}
				});
			}
		}
	});
}
