// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Child table event handlers for Transport Order Package volume calculation
frappe.ui.form.on('Transport Order Package', {
	refresh: function(frm, cdt, cdn) {
		// Recalculate volume when row is refreshed/loaded
		calculate_volume(frm, cdt, cdn);
	},
	length: function(frm, cdt, cdn) {
		calculate_volume(frm, cdt, cdn);
	},
	width: function(frm, cdt, cdn) {
		calculate_volume(frm, cdt, cdn);
	},
	height: function(frm, cdt, cdn) {
		calculate_volume(frm, cdt, cdn);
	}
});

function calculate_volume(frm, cdt, cdn) {
	const doc = frappe.get_doc(cdt, cdn);
	const length = parseFloat(doc.length) || 0;
	const width = parseFloat(doc.width) || 0;
	const height = parseFloat(doc.height) || 0;
	
	if (length > 0 && width > 0 && height > 0) {
		const volume = length * width * height;
		frappe.model.set_value(cdt, cdn, 'volume', volume);
	} else {
		frappe.model.set_value(cdt, cdn, 'volume', 0);
	}
}
