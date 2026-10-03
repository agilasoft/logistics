// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Quote Warehouse', {
	item: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.item) {
			const item = row.item;
			const unit_cost_at_fetch = parseFloat(row.unit_cost) || 0;
			// Default from the item only. A cost the user types must not be cleared
			// when the item has no standard unit cost.
			frappe.db.get_value('Item', item, 'custom_standard_unit_cost', (r) => {
				const current = locals[cdt] && locals[cdt][cdn];
				if (!current || current.item !== item) {
					return;
				}
				if ((parseFloat(current.unit_cost) || 0) !== unit_cost_at_fetch) {
					return;
				}
				if (r && r.custom_standard_unit_cost) {
					frappe.model.set_value(cdt, cdn, 'unit_cost', r.custom_standard_unit_cost);
				} else if (!unit_cost_at_fetch) {
					frappe.model.set_value(cdt, cdn, 'unit_cost', 0);
				}
			});
		} else {
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

