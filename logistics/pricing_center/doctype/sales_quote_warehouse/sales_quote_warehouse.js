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
	},
	calculation_method: function(frm, cdt, cdn) {
		// Trigger refresh to show/hide dependent fields
		frm.refresh_field('items');
		// Calculate estimated revenue when calculation method changes
		calculate_estimated_revenue(frm, cdt, cdn);
	},
	unit_rate: function(frm, cdt, cdn) {
		calculate_estimated_revenue(frm, cdt, cdn);
	},
	minimum_quantity: function(frm, cdt, cdn) {
		calculate_estimated_revenue(frm, cdt, cdn);
	},
	minimum_charge: function(frm, cdt, cdn) {
		calculate_estimated_revenue(frm, cdt, cdn);
	},
	maximum_charge: function(frm, cdt, cdn) {
		calculate_estimated_revenue(frm, cdt, cdn);
	},
	base_amount: function(frm, cdt, cdn) {
		calculate_estimated_revenue(frm, cdt, cdn);
	}
});

function calculate_estimated_revenue(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (row.calculation_method && row.unit_rate) {
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_warehouse.sales_quote_warehouse.calculate_estimated_revenue_for_row',
			args: {
				doc: row
			},
			callback: function(r) {
				if (r.message && r.message.estimated_revenue !== undefined) {
					frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue);
				}
			}
		});
	}
}

