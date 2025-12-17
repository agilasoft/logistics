// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Air Booking', {
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
					__('Are you sure you want to convert this Air Booking to an Air Shipment?'),
					function() {
						frm.call({
							method: 'convert_to_shipment',
							doc: frm.doc,
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.set_route('Form', 'Air Shipment', r.message.air_shipment);
								}
							}
						});
					}
				);
			}, __('Actions'));
		}
	}
});

