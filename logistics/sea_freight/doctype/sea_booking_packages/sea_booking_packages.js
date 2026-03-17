// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).

// Helper to check if grid form dialog is open (comprehensive check)
function _is_grid_dialog_open() {
	// Check for cur_dialog (Frappe's dialog state)
	if (typeof cur_dialog !== 'undefined' && cur_dialog && cur_dialog.display) {
		return true;
	}
	
	// Check for open grid row (most reliable way to detect grid form is open)
	if ($('.grid-row-open').length > 0) return true;
	
	// Check for grid form dialog
	if ($('.grid-form-dialog:visible').length > 0) return true;
	
	// Check for grid row form wrapper visible
	if ($('.grid-row-form:visible, .grid-form-body:visible').length > 0) return true;
	
	// Check for modal dialogs
	if ($('.modal:visible, .form-dialog:visible').length > 0) {
		// Additional check: if it's a grid row dialog
		if ($('.modal:visible .grid-row-form, .form-dialog:visible .grid-row-form').length > 0) {
			return true;
		}
	}
	
	return false;
}

frappe.ui.form.on('Sea Booking Packages', {
	refresh: function(frm, cdt, cdn) {
		var _cdt = cdt || (frm && frm.doctype);
		var _cdn = cdn || (frm && frm.doc && frm.doc.name);
		// Only call volume calculation if dialog is not open (prevents freeze message)
		// For child tables, allow calculation even if parent form is new
		if (_cdt && _cdn && !_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			// For child tables (cdt is provided), always allow calculation
			// For main forms, only if form is not new
			if (cdt || !frm || (!frm.is_new() && !frm.doc.__islocal)) {
				logistics_calculate_volume_from_dimensions(frm, _cdt, _cdn);
			}
		}
		// Chargeable weight is computed on parent Sea Booking
	},
	length: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			_trigger_parent_aggregation(frm);
		}
	},
	width: function(frm, cdt, cdn) {
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			_trigger_parent_aggregation(frm);
		}
	},
	height: function(frm, cdt, cdn) {
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			_trigger_parent_aggregation(frm);
		}
	},
	dimension_uom: function(frm, cdt, cdn) {
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			_trigger_parent_aggregation(frm);
		}
	},
	volume_uom: function(frm, cdt, cdn) {
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_trigger_parent_aggregation(frm);
	},
	volume: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm);
	},
	weight: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm);
	},
	weight_uom: function(frm, cdt, cdn) {
		_trigger_parent_aggregation(frm);
	},
	commodity: function(frm, cdt, cdn) {
		// Don't make API calls or set values if dialog is open (prevents freeze messages)
		// Rely on server-side validation for any updates when dialog is open
		if (_is_grid_dialog_open()) {
			return;
		}
		
		// Populate HS code from commodity's default_hs_code
		let row = locals[cdt][cdn];
		if (row.commodity) {
			frappe.db.get_value('Commodity', row.commodity, 'default_hs_code', (r) => {
				// Double-check dialog is still closed before setting value
				if (_is_grid_dialog_open()) {
					return;
				}
				if (r && r.default_hs_code) {
					frappe.model.set_value(cdt, cdn, 'hs_code', r.default_hs_code);
				} else {
					// Clear HS code if commodity doesn't have a default HS code
					frappe.model.set_value(cdt, cdn, 'hs_code', '');
				}
			});
		} else {
			// Clear HS code if commodity is cleared
			frappe.model.set_value(cdt, cdn, 'hs_code', '');
		}
	}
});

// Trigger parent Sea Booking aggregation (chargeable weight computed on parent)
function _trigger_parent_aggregation(frm) {
	if (!frm || frm.doctype !== 'Sea Booking') return;
	if (typeof window._sea_booking_debounced_aggregate_packages === 'function') {
		window._sea_booking_debounced_aggregate_packages(frm);
	}
}
