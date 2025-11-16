// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Quote Warehouse', {
	item: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item) {
			// Fetch standard unit cost from item
			frappe.db.get_value('Item', row.item, 'custom_standard_unit_cost', (r) => {
				if (r && r.custom_standard_unit_cost) {
					// Set unit_cost with the standard unit cost
					frappe.model.set_value(cdt, cdn, 'unit_cost', r.custom_standard_unit_cost);
				} else {
					// Clear unit_cost if no standard cost is found
					frappe.model.set_value(cdt, cdn, 'unit_cost', 0);
				}
			});
		} else {
			// Clear unit_cost if item is cleared
			frappe.model.set_value(cdt, cdn, 'unit_cost', 0);
		}
	}
});

