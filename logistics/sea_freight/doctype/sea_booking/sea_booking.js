// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sea Booking', {
	refresh: function(frm) {
		// Add button to fetch quotations
		if (frm.doc.sales_quote) {
			frm.add_custom_button(__('Fetch Quotations'), function() {
				frm.call({
					method: 'fetch_quotations',
					doc: frm.doc,
					callback: function(r) {
						if (r.message && r.message.success) {
							frm.reload_doc();
						}
					}
				});
			}, __('Actions'));
		}
		
		// Add button to convert to shipment
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Convert to Shipment'), function() {
				frappe.confirm(
					__('Are you sure you want to convert this Sea Booking to a Sea Shipment?'),
					function() {
						frm.call({
							method: 'convert_to_shipment',
							doc: frm.doc,
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.set_route('Form', 'Sea Shipment', r.message.sea_shipment);
								}
							}
						});
					}
				);
			}, __('Actions'));
		}
	}
});

