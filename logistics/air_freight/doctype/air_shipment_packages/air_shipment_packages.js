// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: volume-from-dimensions (change-only on blur), fallback when grid form open.

function _air_shipment_packages_volume_fallback(frm, cdt, cdn) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form(), 'packages');
}

function _recalc_package_volume(frm, cdt, cdn) {
	var fn = window.logistics_calculate_volume_from_dimensions;
	if (typeof fn === 'function') fn(frm, cdt, cdn);
	else _air_shipment_packages_volume_fallback(frm, cdt, cdn);
}

function _trigger_air_shipment_parent_totals(frm) {
	if (!frm || frm.doctype !== 'Air Shipment' || !frm.doc) return;
	if (frm.doc.override_volume_weight) return;
	if (typeof frm.call !== 'function') return;
	frm.call({
		method: 'aggregate_volume_from_packages_api',
		freeze: false,
		callback: function(r) {
			if (r && !r.exc && r.message) {
				if (r.message.total_volume !== undefined) frm.set_value('total_volume', r.message.total_volume);
				if (r.message.total_weight !== undefined) frm.set_value('total_weight', r.message.total_weight);
			}
		}
	});
}

frappe.ui.form.on('Air Shipment Packages', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === 'function') fn_debounced(frm, cdt, cdn);
			else _air_shipment_packages_volume_fallback(frm, cdt, cdn);
		}, 50);
	},
	refresh: function(frm) {
		var cdt = frm.doctype || 'Air Shipment Packages';
		var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
		if (!cdn || !frm.doc || !(frm.doc.length || frm.doc.width || frm.doc.height)) return;
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_shipment_packages_volume_fallback(frm, cdt, cdn);
	},
	length: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	width: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	height: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	dimension_uom: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	volume_uom: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	no_of_packs: function(frm, cdt, cdn) {
		_recalc_package_volume(frm, cdt, cdn);
	},
	volume: function(frm, cdt, cdn) {
		_trigger_air_shipment_parent_totals(frm);
	}
});
