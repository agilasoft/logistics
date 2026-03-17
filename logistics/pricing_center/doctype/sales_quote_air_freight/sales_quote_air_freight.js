// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, see license.txt

// Weight/Qty Break dialogs are defined in charge_break_dialogs.js (loaded first via app_include_js and doctype_js)

// Sales Quote Air Freight form events - use window. to ensure dialog functions are available
frappe.ui.form.on('Sales Quote Air Freight', {
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
