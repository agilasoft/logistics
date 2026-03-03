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
		// Calculate chargeable weight when form loads
		if (_cdt && _cdn) {
			var row = locals[_cdt] && locals[_cdt][_cdn] ? locals[_cdt][_cdn] : null;
			// Calculate if row exists and has weight or volume (including 0 values)
			if (row && (row.weight !== undefined || row.volume !== undefined)) {
				// Use setTimeout to ensure form context is fully initialized
				setTimeout(function() {
					_calculate_package_chargeable_weight(frm, _cdt, _cdn);
				}, 50);
			}
		}
	},
	length: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			// Trigger chargeable weight calculation after volume is calculated
			setTimeout(function() {
				_calculate_package_chargeable_weight(frm, cdt, cdn);
			}, 300);
		}
	},
	width: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			// Trigger chargeable weight calculation after volume is calculated
			setTimeout(function() {
				_calculate_package_chargeable_weight(frm, cdt, cdn);
			}, 300);
		}
	},
	height: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			// Trigger chargeable weight calculation after volume is calculated
			setTimeout(function() {
				_calculate_package_chargeable_weight(frm, cdt, cdn);
			}, 300);
		}
	},
	dimension_uom: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			// Trigger chargeable weight calculation after volume is calculated
			setTimeout(function() {
				_calculate_package_chargeable_weight(frm, cdt, cdn);
			}, 300);
		}
	},
	volume_uom: function(frm, cdt, cdn) {
		// Don't call if dialog is open (prevents freeze message)
		if (!_is_grid_dialog_open() && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		// Calculate chargeable weight (allowed even when dialog is open)
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	volume: function(frm, cdt, cdn) {
		// Calculate chargeable weight (allowed even when dialog is open)
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight: function(frm, cdt, cdn) {
		// Calculate chargeable weight (allowed even when dialog is open)
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight_uom: function(frm, cdt, cdn) {
		// Calculate chargeable weight (allowed even when dialog is open)
		_calculate_package_chargeable_weight(frm, cdt, cdn);
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

// Cache for Sea Freight Settings to avoid repeated API calls
var _sea_freight_settings_cache = {
	volume_to_weight_factor: null,
	chargeable_weight_calculation: null,
	timestamp: null,
	cache_duration: 5 * 60 * 1000 // 5 minutes
};

function _get_sea_freight_settings(callback) {
	// Check cache first
	var now = new Date().getTime();
	if (_sea_freight_settings_cache.volume_to_weight_factor !== null &&
		_sea_freight_settings_cache.timestamp &&
		(now - _sea_freight_settings_cache.timestamp) < _sea_freight_settings_cache.cache_duration) {
		// Use cached values
		callback(
			_sea_freight_settings_cache.volume_to_weight_factor,
			_sea_freight_settings_cache.chargeable_weight_calculation || 'Higher of Both'
		);
		return;
	}
	
	// Get settings from Sea Freight Settings
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Sea Freight Settings',
			name: 'Sea Freight Settings',
			fieldname: ['volume_to_weight_factor', 'chargeable_weight_calculation']
		},
		freeze: false,
		callback: function(r) {
			var factor = 1000; // Default (equivalent to 1000 kg/m³ factor)
			var calculation_method = 'Higher of Both'; // Default
			
			if (r && r.message) {
				if (r.message.volume_to_weight_factor) {
					factor = parseFloat(r.message.volume_to_weight_factor) || 1000;
				}
				if (r.message.chargeable_weight_calculation) {
					calculation_method = r.message.chargeable_weight_calculation;
				}
			}
			
			// Cache the values
			_sea_freight_settings_cache.volume_to_weight_factor = factor;
			_sea_freight_settings_cache.chargeable_weight_calculation = calculation_method;
			_sea_freight_settings_cache.timestamp = now;
			
			callback(factor, calculation_method);
		},
		error: function(r) {
			// On error, use defaults
			callback(1000, 'Higher of Both');
		}
	});
}

function _calculate_package_chargeable_weight(frm, cdt, cdn) {
	// Calculate chargeable weight for a package row in the child table
	// Simplified version following Air Booking pattern
	if (!cdt || !cdn) {
		return;
	}
	
	// Get form context if not provided
	if (!frm && typeof cur_frm !== 'undefined' && cur_frm) {
		frm = cur_frm;
	}
	
	// Try to get form from open forms if still not available
	if (!frm) {
		try {
			var forms = frappe.ui.form.get_open_forms();
			for (var form_name in forms) {
				var form = forms[form_name];
				// For child tables, find the parent form (Sea Booking)
				if (form && form.doctype === 'Sea Booking') {
					frm = form;
					break;
				}
			}
		} catch(e) {
			// Ignore errors finding form
		}
	}
	
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) {
		return;
	}
	
	var package_volume = parseFloat(row.volume || 0) || 0;
	var package_weight = parseFloat(row.weight || 0) || 0;
	
	// If both volume and weight are zero or missing, set chargeable weight to 0
	if (package_volume <= 0 && package_weight <= 0) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight', 0);
		return;
	}
	
	// Get settings and calculate
	_get_sea_freight_settings(function(factor, calculation_method) {
		// Convert factor (kg/m³) to divisor: divisor = 1,000,000 / factor
		var divisor = 1000000.0 / factor;
		
		// Get latest row state to avoid stale data
		var current_row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
		if (!current_row) return;
		
		// Re-read values from current row
		var volume = parseFloat(current_row.volume || 0) || 0;
		var weight = parseFloat(current_row.weight || 0) || 0;
		
		// Note: Volume should already be in m³ and weight in kg from the conversion system
		// Calculate volume weight: volume (m³) * 1,000,000 / divisor
		var volume_weight = 0;
		if (volume > 0 && divisor && divisor > 0) {
			volume_weight = volume * (1000000.0 / divisor);
		}
		
		// Calculate chargeable weight based on calculation method
		var chargeable = 0;
		if (calculation_method === 'Actual Weight') {
			chargeable = weight;
		} else if (calculation_method === 'Volume Weight') {
			chargeable = volume_weight;
		} else { // 'Higher of Both' (default)
			if (weight > 0 && volume_weight > 0) {
				chargeable = Math.max(weight, volume_weight);
			} else if (weight > 0) {
				chargeable = weight;
			} else if (volume_weight > 0) {
				chargeable = volume_weight;
			} else {
				chargeable = 0;
			}
		}
		
		frappe.model.set_value(cdt, cdn, 'chargeable_weight', chargeable);
		
		// Set chargeable_weight_uom to match weight_uom if not set
		if (!current_row.chargeable_weight_uom && current_row.weight_uom) {
			frappe.model.set_value(cdt, cdn, 'chargeable_weight_uom', current_row.weight_uom);
		}
	});
}
