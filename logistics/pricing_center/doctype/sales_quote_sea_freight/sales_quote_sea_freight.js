// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Sales Quote Sea Freight Client Script

frappe.ui.form.on('Sales Quote Sea Freight', {
	// Revenue calculation triggers
	calculation_method: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	quantity: function(frm, cdt, cdn) {
		// Trigger calculation when quantity changes
		trigger_calculation(frm, cdt, cdn);
	},
	
	unit_rate: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	unit_type: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	minimum_quantity: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	minimum_unit_rate: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	minimum_charge: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	maximum_charge: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	base_amount: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	base_quantity: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	currency: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	uom: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	// Cost calculation triggers
	cost_calculation_method: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_quantity: function(frm, cdt, cdn) {
		// Trigger calculation when cost quantity changes
		trigger_calculation(frm, cdt, cdn);
	},
	
	unit_cost: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_unit_type: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_quantity: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_unit_rate: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_minimum_charge: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_maximum_charge: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_base_amount: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_base_quantity: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_currency: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	cost_uom: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	
	// Tariff triggers
	tariff: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	revenue_tariff: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	cost_tariff: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	use_tariff_in_revenue: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
	},
	use_tariff_in_cost: function(frm, cdt, cdn) {
		trigger_calculation(frm, cdt, cdn);
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

// Function to trigger calculations
function trigger_calculation(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	
	// Debounce the calculation to avoid too many calls
	if (row._calculation_timeout) {
		clearTimeout(row._calculation_timeout);
	}
	
	row._calculation_timeout = setTimeout(function() {
		// Get current row data
		let line_data = {
			item_code: row.item_code,
			item_name: row.item_name,
			calculation_method: row.calculation_method,
			quantity: row.quantity,
			unit_rate: row.unit_rate,
			unit_type: row.unit_type,
			minimum_quantity: row.minimum_quantity,
			minimum_unit_rate: row.minimum_unit_rate,
			minimum_charge: row.minimum_charge,
			maximum_charge: row.maximum_charge,
			base_amount: row.base_amount,
			base_quantity: row.base_quantity,
			currency: row.currency,
			uom: row.uom,
			cost_calculation_method: row.cost_calculation_method,
			cost_quantity: row.cost_quantity,
			unit_cost: row.unit_cost,
			cost_unit_type: row.cost_unit_type,
			cost_minimum_quantity: row.cost_minimum_quantity,
			cost_minimum_unit_rate: row.cost_minimum_unit_rate,
			cost_minimum_charge: row.cost_minimum_charge,
			cost_maximum_charge: row.cost_maximum_charge,
			cost_base_amount: row.cost_base_amount,
			cost_base_quantity: row.cost_base_quantity,
			cost_currency: row.cost_currency,
			cost_uom: row.cost_uom,
			use_tariff_in_revenue: row.use_tariff_in_revenue,
			use_tariff_in_cost: row.use_tariff_in_cost,
			tariff: row.tariff,
			revenue_tariff: row.revenue_tariff,
			cost_tariff: row.cost_tariff,
			parent: frm.doc.name,
			parenttype: frm.doc.doctype
		};
		
		// Call the calculation API
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_sea_freight.sales_quote_sea_freight.calculate_sea_freight_line',
			args: {
				line_data: JSON.stringify(line_data)
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					// Update the row with calculated values
					frappe.model.set_value(cdt, cdn, 'estimated_revenue', r.message.estimated_revenue || 0);
					frappe.model.set_value(cdt, cdn, 'estimated_cost', r.message.estimated_cost || 0);
					frappe.model.set_value(cdt, cdn, 'revenue_calc_notes', r.message.revenue_calc_notes || '');
					frappe.model.set_value(cdt, cdn, 'cost_calc_notes', r.message.cost_calc_notes || '');
					
					// Update quantity if recalculated
					if (r.message.quantity !== undefined && r.message.quantity !== null) {
						frappe.model.set_value(cdt, cdn, 'quantity', r.message.quantity);
					}
					
					// Refresh the field to show updated values
					frm.refresh_field('sea_freight');
				} else {
					console.log('Calculation failed:', r.message);
				}
			},
			error: function(err) {
				console.log('Calculation API error:', err);
			}
		});
	}, 500); // 500ms debounce
}
