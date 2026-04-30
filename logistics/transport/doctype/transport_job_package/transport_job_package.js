// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, see license.txt
// Volume-from-dimensions (change-only on blur), fallback when grid form open.
// Parent totals (total_weight / total_volume / total_packages) refresh via aggregate_volume_from_packages (Transport Order pattern).

function _transport_job_package_volume_fallback(frm, cdt, cdn) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form(), 'packages');
}

function _trigger_parent_aggregation(frm, delay_ms) {
	if (!frm || frm.doctype !== 'Transport Job') return;
	if (frm.is_new() || frm.doc.__islocal) return;
	var run = function() {
		frm.trigger('aggregate_volume_from_packages');
	};
	if (delay_ms) {
		setTimeout(run, delay_ms);
	} else {
		run();
	}
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
		_trigger_parent_aggregation(frm, 100);
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
		_trigger_parent_aggregation(frm, 100);
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
		_trigger_parent_aggregation(frm, 100);
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
		_trigger_parent_aggregation(frm, 100);
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _transport_job_package_volume_fallback(frm, cdt, cdn);
		_trigger_parent_aggregation(frm, 100);
	},
	volume: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm);
	},
	weight: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm);
	},
	weight_uom: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm, 100);
	},
	no_of_packs: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_trigger_parent_aggregation(frm);
	},
	quantity: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_trigger_parent_aggregation(frm);
	}
});
