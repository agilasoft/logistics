// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: volume-from-dimensions (change-only on blur), fallback when grid form open.

function _sea_freight_packages_volume_fallback(frm, cdt, cdn) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form(), 'packages');
}

frappe.ui.form.on('Sea Freight Packages', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === 'function') fn_debounced(frm, cdt, cdn);
			else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
		}, 50);
	},
	refresh: function(frm) {
		var cdt = frm.doctype || 'Sea Freight Packages';
		var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
		if (!cdn || !frm.doc || !(frm.doc.length || frm.doc.width || frm.doc.height)) return;
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	},
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _sea_freight_packages_volume_fallback(frm, cdt, cdn);
	}
});
