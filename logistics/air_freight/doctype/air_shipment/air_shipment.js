// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Air Shipment", {
	refresh(frm) {
		console.log("Air Shipment form refreshed");
		console.log("Origin Port:", frm.doc.origin_port);
		console.log("Destination Port:", frm.doc.destination_port);
		
		// Update DG compliance status on form load
		if (frm.doc.contains_dangerous_goods) {
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
		
		// Check for dangerous goods and show alert only if non-compliant
		frm.call('get_dg_dashboard_info').then(r => {
			if (r.message && r.message.has_dg && r.message.compliance_status === 'Non-Compliant') {
				show_dg_alert(frm, r.message);
			}
		}).catch(err => {
			console.error("Error getting DG dashboard info:", err);
		});
		
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

// Package table field change handlers for dangerous goods
frappe.ui.form.on("Air Shipment Packages", {
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
	} else if (!has_dg && contains_dg) {
		frm.set_value('contains_dangerous_goods', 0);
		remove_dg_alert(frm);
	} else if (has_dg && contains_dg) {
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
	
	// Refresh milestone view to update DG compliance badge
	refresh_milestone_view(frm);
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
