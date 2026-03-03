// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Weight break button handlers - uses shared open_weight_break_rate_dialog from sales_quote_air_freight.js
frappe.ui.form.on('Sales Quote Sea Freight', {
	// Revenue calculation triggers
	calculation_method: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	unit_rate: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	unit_type: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	minimum_quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	minimum_unit_rate: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	minimum_charge: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	maximum_charge: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	base_amount: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	base_quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	currency: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	uom: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	
	// Cost calculation triggers
	cost_calculation_method: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	unit_cost: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_unit_type: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_minimum_quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_minimum_unit_rate: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_minimum_charge: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_maximum_charge: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_base_amount: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_base_quantity: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_currency: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	cost_uom: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	
	// Tariff triggers
	tariff: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	use_tariff_in_revenue: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	use_tariff_in_cost: function(frm, cdt, cdn) {
		calculate_charges(frm, cdt, cdn);
	},
	
	// Weight break button handlers (Manage Selling Weight Breaks / Manage Cost Weight Breaks)
	selling_weight_break: function(frm, cdt, cdn) {
		const row = (cdn && cdt) ? frappe.get_doc(cdt, cdn) : (frm && frm.selected_doc) ? frm.selected_doc : null;
		if (!row) return;
		if (typeof window.open_weight_break_rate_dialog === 'function') {
			window.open_weight_break_rate_dialog(frm, row, 'Selling');
		} else {
			frappe.msgprint({ title: __('Error'), message: __('Weight Break dialog is not loaded. Please refresh the page.'), indicator: 'red' });
		}
	},
	cost_weight_break: function(frm, cdt, cdn) {
		const row = (cdn && cdt) ? frappe.get_doc(cdt, cdn) : (frm && frm.selected_doc) ? frm.selected_doc : null;
		if (!row) return;
		if (typeof window.open_weight_break_rate_dialog === 'function') {
			window.open_weight_break_rate_dialog(frm, row, 'Cost');
		} else {
			frappe.msgprint({ title: __('Error'), message: __('Weight Break dialog is not loaded. Please refresh the page.'), indicator: 'red' });
		}
	},
	selling_qty_break: function(frm, cdt, cdn) {
		const row = (cdn && cdt) ? frappe.get_doc(cdt, cdn) : (frm && frm.selected_doc) ? frm.selected_doc : null;
		if (!row) return;
		if (typeof window.open_qty_break_rate_dialog === 'function') {
			window.open_qty_break_rate_dialog(frm, row, 'Selling');
		} else {
			frappe.msgprint({ title: __('Error'), message: __('Qty Break dialog is not loaded. Please refresh the page.'), indicator: 'red' });
		}
	},
	cost_qty_break: function(frm, cdt, cdn) {
		const row = (cdn && cdt) ? frappe.get_doc(cdt, cdn) : (frm && frm.selected_doc) ? frm.selected_doc : null;
		if (!row) return;
		if (typeof window.open_qty_break_rate_dialog === 'function') {
			window.open_qty_break_rate_dialog(frm, row, 'Cost');
		} else {
			frappe.msgprint({ title: __('Error'), message: __('Qty Break dialog is not loaded. Please refresh the page.'), indicator: 'red' });
		}
	}
});

/**
 * Calculate charges (revenue and cost) for a Sales Quote Sea Freight row
 */
function calculate_charges(frm, cdt, cdn) {
	if (!cdn) {
		return;
	}
	
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	
	// Get parent document name if available
	let parent_name = row.parent;
	if (!parent_name && frm && frm.doc && frm.doc.name) {
		parent_name = frm.doc.name;
	}
	
	// Get current row data
	const row_data = {
		item_code: row.item_code,
		item_name: row.item_name,
		calculation_method: row.calculation_method,
		quantity: row.quantity,
		uom: row.uom,
		currency: row.currency,
		unit_rate: row.unit_rate,
		unit_type: row.unit_type,
		minimum_quantity: row.minimum_quantity,
		minimum_unit_rate: row.minimum_unit_rate,
		minimum_charge: row.minimum_charge,
		maximum_charge: row.maximum_charge,
		base_amount: row.base_amount,
		base_quantity: row.base_quantity,
		cost_calculation_method: row.cost_calculation_method,
		cost_quantity: row.cost_quantity,
		cost_uom: row.cost_uom,
		cost_currency: row.cost_currency,
		unit_cost: row.unit_cost,
		cost_unit_type: row.cost_unit_type,
		cost_minimum_quantity: row.cost_minimum_quantity,
		cost_minimum_unit_rate: row.cost_minimum_unit_rate,
		cost_minimum_charge: row.cost_minimum_charge,
		cost_maximum_charge: row.cost_maximum_charge,
		cost_base_amount: row.cost_base_amount,
		cost_base_quantity: row.cost_base_quantity,
		tariff: row.tariff,
		use_tariff_in_revenue: row.use_tariff_in_revenue,
		use_tariff_in_cost: row.use_tariff_in_cost,
		parent: parent_name,
		parenttype: row.parenttype || 'Sales Quote'
	};
	
	// Call server method to calculate charges
	frappe.call({
		method: 'logistics.pricing_center.doctype.sales_quote_sea_freight.sales_quote_sea_freight.trigger_sea_freight_calculations_for_line',
		args: {
			line_data: row_data
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				// Update estimated revenue
				if (r.message.estimated_revenue !== undefined) {
					frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue);
				}
				
				// Update estimated cost
				if (r.message.estimated_cost !== undefined) {
					frappe.model.set_value(cdt, cdn, 'estimated_cost', r.message.estimated_cost);
				}
				
				// Update calculation notes
				if (r.message.revenue_calc_notes !== undefined) {
					frappe.model.set_value(cdt, cdn, 'revenue_calc_notes', r.message.revenue_calc_notes);
				}
				
				if (r.message.cost_calc_notes !== undefined) {
					frappe.model.set_value(cdt, cdn, 'cost_calc_notes', r.message.cost_calc_notes);
				}
				
				// Update quantity if calculated
				if (r.message.quantity !== undefined && r.message.quantity !== null) {
					frappe.model.set_value(cdt, cdn, 'quantity', r.message.quantity);
				}
			}
		},
		error: function(err) {
			// Silently fail - calculations will happen on save
			// Only log if it's not a common validation error
			if (err && err.exc && !err.exc.includes('ValidationError')) {
				console.error('Error calculating charges:', err);
			}
		}
	});
}
