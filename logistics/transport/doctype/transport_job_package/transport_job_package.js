// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, see license.txt
// Volume-from-dimensions (change-only on blur), fallback when grid form open.

function _transport_job_package_volume_fallback(frm, cdt, cdn) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form(), 'packages');
}

frappe.ui.form.on("Transport Job Package", {
	form_load: function (frm, cdt, cdn) {
		var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : (frm && frm.doc);
		if (!row || (row.weight_uom && row.volume_uom)) return;
		frappe.call({
			method: "logistics.utils.default_uom.get_default_uoms_for_domain_api",
			args: { domain: "transport" },
			callback: function (r) {
				if (r.message) {
					var _cdt = cdt || (frm && frm.doctype);
					var _cdn = cdn || (frm && frm.doc && frm.doc.name);
					if (_cdt && _cdn) {
						if (!row.weight_uom && r.message.weight_uom) {
							frappe.model.set_value(_cdt, _cdn, "weight_uom", r.message.weight_uom);
						}
						if (!row.volume_uom && r.message.volume_uom) {
							frappe.model.set_value(_cdt, _cdn, "volume_uom", r.message.volume_uom);
						}
					}
				}
			},
		});
	},
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') fn_immediate(frm, cdt, cdn);
			else if (typeof fn_debounced === 'function') fn_debounced(frm, cdt, cdn);
			else _transport_job_package_volume_fallback(frm, cdt, cdn);
		}, 50);
	},
	refresh: function(frm) {
		var cdt = frm.doctype || 'Transport Job Package';
		var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
		if (!cdn || !frm.doc || !(frm.doc.length || frm.doc.width || frm.doc.height)) return;
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	},
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
	}
});
