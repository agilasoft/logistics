// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).

frappe.ui.form.on('Air Booking Packages', {
	refresh: function(frm) {
		// Recompute volume from dimensions when form loads (e.g. child form in dialog)
		if (frm.doc && (frm.doc.length || frm.doc.width || frm.doc.height)) {
			var cdt = frm.doctype || 'Air Booking Packages';
			var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
			if (!cdn) return;
			if (typeof logistics_calculate_volume_from_dimensions === 'function') {
				logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
			}
		}
		// Calculate chargeable weight when form loads
		if (frm.doc && (frm.doc.weight || frm.doc.volume)) {
			_calculate_package_chargeable_weight(frm);
		}
	},
	length: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	width: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	height: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	dimension_uom: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	volume_uom: function(frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	volume: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm);
	},
	weight: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm);
	},
	weight_uom: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm);
	}
});

function _calculate_package_chargeable_weight(frm) {
	// Calculate chargeable weight for this package using parent Air Booking divisor settings
	if (!frm.doc.weight && !frm.doc.volume) {
		frm.set_value('chargeable_weight', 0);
		return;
	}
	
	// Get parent Air Booking to get divisor settings
	var parent_name = frm.doc.parent || (frm.cur_frm && frm.cur_frm.doc && frm.cur_frm.doc.name);
	if (!parent_name) {
		// Try to get from the form's parent if this is a child table row
		if (frm.cur_frm && frm.cur_frm.doc) {
			parent_name = frm.cur_frm.doc.name;
		} else {
			return; // Can't calculate without parent
		}
	}
	
	// Get divisor from parent Air Booking
	frappe.db.get_value('Air Booking', parent_name, [
		'volume_to_weight_factor_type',
		'custom_volume_to_weight_divisor',
		'airline'
	], function(r) {
		if (!r) return;
		
		var divisor = 6000; // Default IATA
		var factor_type = r.volume_to_weight_factor_type || 'IATA';
		
		if (factor_type === 'IATA') {
			divisor = 6000;
		} else if (factor_type === 'Custom') {
			if (r.custom_volume_to_weight_divisor) {
				divisor = parseFloat(r.custom_volume_to_weight_divisor) || 6000;
			} else if (r.airline) {
				// Fetch airline divisor
				frappe.db.get_value('Airline', r.airline, 'volume_to_weight_divisor', function(airline_r) {
					if (airline_r && airline_r.volume_to_weight_divisor) {
						divisor = parseFloat(airline_r.volume_to_weight_divisor) || 6000;
					}
					_calculate_and_set_package_chargeable_weight(frm, divisor);
				});
				return; // Will continue in callback
			}
		}
		
		_calculate_and_set_package_chargeable_weight(frm, divisor);
	});
}

function _calculate_and_set_package_chargeable_weight(frm, divisor) {
	var volume_weight = 0;
	var chargeable = 0;
	var package_volume = parseFloat(frm.doc.volume || 0);
	var package_weight = parseFloat(frm.doc.weight || 0);
	
	// Note: Volume should already be in m³ from the conversion system
	// Calculate volume weight: volume (m³) * 1,000,000 / divisor
	if (package_volume > 0 && divisor) {
		volume_weight = package_volume * (1000000.0 / divisor);
	}
	
	// Chargeable weight is higher of actual weight or volume weight
	if (package_weight > 0 && volume_weight > 0) {
		chargeable = Math.max(package_weight, volume_weight);
	} else if (package_weight > 0) {
		chargeable = package_weight;
	} else if (volume_weight > 0) {
		chargeable = volume_weight;
	}
	
	frm.set_value('chargeable_weight', chargeable);
	
	// Set chargeable_weight_uom to match weight_uom if not set
	if (!frm.doc.chargeable_weight_uom && frm.doc.weight_uom) {
		frm.set_value('chargeable_weight_uom', frm.doc.weight_uom);
	}
}
