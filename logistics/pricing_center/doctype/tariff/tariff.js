// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Aligned with Sales Quote Charge: revenue_calculation_method / cost_calculation_method (same order and labels).
const SALES_QUOTE_CALCULATION_METHOD_OPTIONS =
	"Per Unit\nFixed Amount\nFlat Rate\nBase Plus Additional\nFirst Plus Additional\nPercentage\nLocation-based\nWeight Break\nQty Break";

frappe.ui.form.on('Tariff', {
	refresh: function (frm) {
		apply_sales_quote_calc_method_options_to_tariff_grids(frm);
	},

	tariff_type: function (frm) {
		// Clear all customer-related fields when tariff type changes
		frm.set_value('customer', '');
		frm.set_value('customer_group', '');
		frm.set_value('territory', '');
		if (frm.doc.customers) {
			frm.clear_table('customers');
			frm.refresh_field('customers');
		}
		frm.set_value('agent', '');
	},

	valid_from: function (frm) {
		if (frm.doc.valid_from && frm.doc.valid_to && frm.doc.valid_from > frm.doc.valid_to) {
			frappe.msgprint(__('Valid From date cannot be later than Valid To date'));
			frm.set_value('valid_to', '');
		}
	},

	valid_to: function (frm) {
		if (frm.doc.valid_from && frm.doc.valid_to && frm.doc.valid_from > frm.doc.valid_to) {
			frappe.msgprint(__('Valid To date cannot be earlier than Valid From date'));
			frm.set_value('valid_from', '');
		}
	},
});

function apply_sales_quote_calc_method_options_to_tariff_grids(frm) {
	const table_fields = [
		'air_freight_rates',
		'sea_freight_rates',
		'transport_rates',
		'warehouse_rates',
		'customs_rates',
	];
	table_fields.forEach((fieldname) => {
		const grid = frm.fields_dict[fieldname] && frm.fields_dict[fieldname].grid;
		if (grid && grid.update_docfield_property) {
			grid.update_docfield_property(
				'calculation_method',
				'options',
				SALES_QUOTE_CALCULATION_METHOD_OPTIONS
			);
		}
	});
}

// Child table events for rate validation
frappe.ui.form.on('Air Freight Rate', {
	calculation_method: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
	rate_value: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Sea Freight Rate', {
	calculation_method: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
	rate_value: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Transport Rate', {
	calculation_method: function (frm, cdt, cdn) {
		clear_transport_rate_fields_for_method(cdt, cdn);
		validate_rate_entry(frm, cdt, cdn);
	},
	rate_value: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Customs Rate', {
	calculation_method: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
	rate_value: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Warehouse Rate', {
	calculation_method: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
	rate_value: function (frm, cdt, cdn) {
		validate_rate_entry(frm, cdt, cdn);
	},
});

function clear_transport_rate_fields_for_method(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row) return;
	const m = row.calculation_method;
	if (m !== 'Base Plus Additional' && m !== 'Percentage') {
		if (row.base_amount) frappe.model.set_value(cdt, cdn, 'base_amount', null);
	}
	if (m !== 'First Plus Additional' && row.minimum_quantity) {
		frappe.model.set_value(cdt, cdn, 'minimum_quantity', null);
	}
	if (m !== 'Per Unit' && m !== 'First Plus Additional') {
		if (row.minimum_charge) frappe.model.set_value(cdt, cdn, 'minimum_charge', null);
		if (row.maximum_charge) frappe.model.set_value(cdt, cdn, 'maximum_charge', null);
	}
	if (!['Per Unit', 'Weight Break', 'Qty Break'].includes(m) && row.unit_type) {
		frappe.model.set_value(cdt, cdn, 'unit_type', '');
	}
}

function validate_rate_entry(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	// Validate minimum and maximum charges
	if (row.minimum_charge && row.maximum_charge && row.minimum_charge > row.maximum_charge) {
		frappe.msgprint(__('Minimum charge cannot be greater than maximum charge'));
		frappe.model.set_value(cdt, cdn, 'minimum_charge', '');
	}

	// Validate date ranges
	if (row.valid_from && row.valid_to && row.valid_from > row.valid_to) {
		frappe.msgprint(__('Valid From date cannot be later than Valid To date'));
		frappe.model.set_value(cdt, cdn, 'valid_to', '');
	}
}
