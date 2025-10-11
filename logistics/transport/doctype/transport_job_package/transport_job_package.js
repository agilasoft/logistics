// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Job Package', {
	refresh(frm) {
		// Add custom button to calculate volume
		if (frm.doc.length && frm.doc.widht && frm.doc.height) {
			frm.add_custom_button(__('Calculate Volume'), function() {
				calculate_volume(frm);
			});
		}
	},

	length(frm) {
		calculate_volume(frm);
	},

	widht(frm) {
		calculate_volume(frm);
	},

	height(frm) {
		calculate_volume(frm);
	}
});

function calculate_volume(frm) {
	if (frm.doc.length && frm.doc.widht && frm.doc.height) {
		const volume = frm.doc.length * frm.doc.widht * frm.doc.height;
		frm.set_value('volume', volume);
	} else {
		frm.set_value('volume', 0);
	}
}
