// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Dangerous Goods Declaration", {
	refresh(frm) {
		// Add custom buttons
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Generate PDF'), function() {
				frm.call('generate_pdf').then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('PDF Generation'),
							message: r.message.message,
							indicator: r.message.status === 'success' ? 'green' : 'red'
						});
					}
				});
			}, __('Actions'));
			
			frm.add_custom_button(__('Send Notification'), function() {
				frm.call('send_notification').then(r => {
					if (r.message) {
						frappe.msgprint({
							title: __('Notification'),
							message: r.message.message,
							indicator: r.message.status === 'success' ? 'green' : 'red'
						});
					}
				});
			}, __('Actions'));
		}
	},
	
	air_shipment(frm) {
		// Auto-populate fields when Air Freight Job is selected
		if (frm.doc.air_shipment) {
			frm.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Air Shipment',
					name: frm.doc.air_shipment
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('shipper', r.message.shipper);
						frm.set_value('consignee', r.message.consignee);
						frm.set_value('origin_port', r.message.origin_port);
						frm.set_value('destination_port', r.message.destination_port);
						
						// Set emergency contact from Air Freight Job
						if (r.message.dg_emergency_contact) {
							frm.set_value('emergency_contact', r.message.dg_emergency_contact);
						}
						if (r.message.dg_emergency_phone) {
							frm.set_value('emergency_phone', r.message.dg_emergency_phone);
						}
						if (r.message.dg_emergency_email) {
							frm.set_value('emergency_email', r.message.dg_emergency_email);
						}
					}
				}
			});
		}
	}
});

// Child table field change handlers
frappe.ui.form.on("Dangerous Goods Declaration Packages", {
	un_number(frm, cdt, cdn) {
		// Validate UN number format
		let row = locals[cdt][cdn];
		if (row.un_number && !/^\d{4}$/.test(row.un_number)) {
			frappe.msgprint(__("UN Number should be 4 digits"));
		}
	},
	
	is_radioactive(frm, cdt, cdn) {
		// Show/hide radioactive specific fields
		let row = locals[cdt][cdn];
		if (row.is_radioactive) {
			frappe.msgprint(__("Radioactive materials require special handling and documentation"));
		}
	},
	
	temp_controlled(frm, cdt, cdn) {
		// Show/hide temperature specific fields
		let row = locals[cdt][cdn];
		if (row.temp_controlled) {
			frappe.msgprint(__("Temperature controlled materials require temperature range specification"));
		}
	}
});
