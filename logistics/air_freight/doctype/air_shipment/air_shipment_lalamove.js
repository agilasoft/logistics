// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Lalamove Integration for Air Shipment
 */

frappe.ui.form.on('Air Shipment', {
	refresh: function(frm) {
		// Lalamove Integration - only show if last-mile delivery is required
		if (frm.doc.use_lalamove && frm.doc.last_mile_delivery_required && !frm.is_new()) {
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
	}
});


