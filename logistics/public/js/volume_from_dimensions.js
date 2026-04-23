// Copyright (c) 2025, www.agilasoft.com and contributors
// Shared volume-from-dimensions for package doctypes (Air/Sea Booking, Air/Sea Shipment, Transport Order/Job).
// Trigger only on blur (change), not while typing.

(function() {
	'use strict';

	var PACKAGE_DOCTYPES = [
		'Air Booking Packages', 'Sea Booking Packages', 'Air Shipment Packages',
		'Sea Freight Packages', 'Transport Order Package', 'Transport Job Package'
	];

	function _is_package_doctype(doctype) {
		return PACKAGE_DOCTYPES.indexOf(doctype) >= 0;
	}

	function logistics_package_line_volume_multiplier(row) {
		if (!row) return 1;
		var dt = row.doctype;
		var n = parseFloat(row.no_of_packs || 0);
		var q = parseFloat(row.quantity || 0);
		if (dt === 'Transport Order Package' || dt === 'Transport Job Package') {
			return n || q || 1;
		}
		return n || 0;
	}
	window.logistics_package_line_volume_multiplier = logistics_package_line_volume_multiplier;

	function _volume_from_dimensions_fallback(frm, cdt, cdn, grid_row, grid_field) {
		grid_field = grid_field || 'packages';
		if (!frm || !cdt || !cdn) return;
		var row = frappe.get_doc(cdt, cdn);
		if (!row || row.length === undefined) return;
		var length = parseFloat(row.length || 0);
		var width = parseFloat(row.width || 0);
		var height = parseFloat(row.height || 0);
		if (length <= 0 || width <= 0 || height <= 0) {
			frappe.model.set_value(cdt, cdn, 'volume', 0);
			_refresh_volume_field(frm, cdt, cdn, grid_row, grid_field);
			return;
		}
		var dimension_uom = row.dimension_uom;
		var volume_uom = row.volume_uom;
		var company = (frm && frm.doc && frm.doc.company) || frappe.defaults.get_user_default('Company');
		function do_calc(dim_uom, vol_uom) {
			dim_uom = dim_uom || 'CM';
			vol_uom = vol_uom || 'M³';
			frappe.call({
				method: 'logistics.utils.measurements.calculate_volume_from_dimensions_api',
				args: { length: length, width: width, height: height, dimension_uom: dim_uom, volume_uom: vol_uom, company: company },
				freeze: false,
				callback: function(r) {
					var volume = 0;
					if (r && r.message && !r.message.error && r.message.volume != null && !isNaN(parseFloat(r.message.volume))) {
						volume = parseFloat(r.message.volume);
					}
					var row = frappe.get_doc(cdt, cdn);
					volume *= logistics_package_line_volume_multiplier(row);
					frappe.model.set_value(cdt, cdn, 'volume', volume);
					_refresh_volume_field(frm, cdt, cdn, grid_row, grid_field);
					if (frm.trigger) frm.trigger('volume', cdt, cdn);
				},
				error: function() {
					frappe.model.set_value(cdt, cdn, 'volume', 0);
					_refresh_volume_field(frm, cdt, cdn, grid_row, grid_field);
				}
			});
		}
		if (dimension_uom && volume_uom) {
			do_calc(dimension_uom, volume_uom);
		} else {
			frappe.call({
				method: 'logistics.utils.measurements.get_default_uoms_api',
				args: { company: company },
				freeze: false,
				callback: function(r) {
					var def_dim = r && r.message && r.message.dimension ? r.message.dimension : 'CM';
					var def_vol = r && r.message && r.message.volume ? r.message.volume : 'M³';
					if (!dimension_uom && def_dim) frappe.model.set_value(cdt, cdn, 'dimension_uom', def_dim);
					if (!volume_uom && def_vol) frappe.model.set_value(cdt, cdn, 'volume_uom', def_vol);
					do_calc(dimension_uom || def_dim, volume_uom || def_vol);
				},
				error: function() { do_calc('CM', 'M³'); }
			});
		}
	}

	function _refresh_volume_field(frm, cdt, cdn, grid_row, grid_field) {
		grid_field = grid_field || 'packages';
		var cur = frappe.ui.form.get_cur_frm && frappe.ui.form.get_cur_frm();
		if (cur && cur.doctype === cdt && cur.doc && cur.doc.name === cdn && cur.refresh_field) {
			cur.refresh_field('volume');
		} else if (grid_row && grid_row.grid_form && grid_row.grid_form.refresh_field) {
			grid_row.grid_form.refresh_field('volume');
		} else {
			var grid = (grid_row && grid_row.grid) || (frm && frm.fields_dict && frm.fields_dict[grid_field] && frm.fields_dict[grid_field].grid);
			if (grid && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn] && grid.grid_rows_by_docname[cdn].refresh_field) {
				grid.grid_rows_by_docname[cdn].refresh_field('volume');
			}
		}
	}

	// Attach packages grid wrapper change listener (trigger only on blur)
	function attach_packages_change_listener(frm, package_doctype, parentfield, event_ns) {
		event_ns = event_ns || 'volume';
		var grid_row = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
		if (!grid_row || !grid_row.doc || grid_row.doc.doctype !== package_doctype || grid_row.doc.parentfield !== parentfield) return;
		var cdt = grid_row.doc.doctype;
		var cdn = grid_row.doc.name;
		var wrapper = grid_row.grid_form && grid_row.grid_form.wrapper;
		if (!wrapper || !wrapper.length) return;
		var dim_sel = 'input[data-fieldname="length"], input[data-fieldname="width"], input[data-fieldname="height"], input[data-fieldname="dimension_uom"], input[data-fieldname="volume_uom"], input[data-fieldname="no_of_packs"], input[data-fieldname="quantity"], select[data-fieldname="no_of_packs"], select[data-fieldname="quantity"]';
		wrapper.off('change.' + event_ns).on('change.' + event_ns, dim_sel, function(ev) {
			var $form = $(ev.target).closest('.form-in-grid');
			['length', 'width', 'height', 'dimension_uom', 'volume_uom', 'no_of_packs', 'quantity'].forEach(function(fn) {
				var $in = $form.find('input[data-fieldname="' + fn + '"]');
				if ($in.length) {
					var v = $in.val();
					if (fn === 'length' || fn === 'width' || fn === 'height' || fn === 'no_of_packs' || fn === 'quantity') v = parseFloat(v) || 0;
					frappe.model.set_value(cdt, cdn, fn, v);
				}
			});
			var fn = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn === 'function') fn(frm, cdt, cdn);
			else _volume_from_dimensions_fallback(frm, cdt, cdn, grid_row, parentfield);
		});
	}

	// Document-level fallback: trigger only on blur (change)
	$(document).off('change.logistics_volume').on(
		'change.logistics_volume',
		'.form-in-grid input[data-fieldname="length"], .form-in-grid input[data-fieldname="width"], .form-in-grid input[data-fieldname="height"], .form-in-grid input[data-fieldname="dimension_uom"], .form-in-grid input[data-fieldname="volume_uom"], .form-in-grid input[data-fieldname="no_of_packs"], .form-in-grid input[data-fieldname="quantity"], .form-in-grid select[data-fieldname="no_of_packs"], .form-in-grid select[data-fieldname="quantity"]',
		function(ev) {
			var grid_row = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
			if (!grid_row) grid_row = frappe.cur_frm && frappe.cur_frm.cur_grid;
			if (!grid_row || !grid_row.doc || !_is_package_doctype(grid_row.doc.doctype) || grid_row.doc.parentfield !== 'packages') return;
			var frm = grid_row.grid && grid_row.grid.frm;
			if (!frm) frm = frappe.cur_frm;
			if (!frm) return;
			var cdt = grid_row.doc.doctype;
			var cdn = grid_row.doc.name;
			var $form = $(ev.target).closest('.form-in-grid');
			['length', 'width', 'height', 'dimension_uom', 'volume_uom', 'no_of_packs', 'quantity'].forEach(function(fn) {
				var $in = $form.find('input[data-fieldname="' + fn + '"], select[data-fieldname="' + fn + '"]');
				if ($in.length) {
					var v = $in.val();
					if (fn === 'length' || fn === 'width' || fn === 'height' || fn === 'no_of_packs' || fn === 'quantity') v = parseFloat(v) || 0;
					frappe.model.set_value(cdt, cdn, fn, v);
				}
			});
			var fn = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn === 'function') fn(frm, cdt, cdn);
			else _volume_from_dimensions_fallback(frm, cdt, cdn, grid_row, 'packages');
		}
	);

	window.logistics_volume_from_dimensions_fallback = _volume_from_dimensions_fallback;
	window.logistics_refresh_volume_field = _refresh_volume_field;
	window.logistics_attach_packages_change_listener = attach_packages_change_listener;
})();
