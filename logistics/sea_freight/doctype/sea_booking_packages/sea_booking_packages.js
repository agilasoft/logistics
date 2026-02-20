// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).

frappe.ui.form.on('Sea Booking Packages', {
	refresh: function(frm, cdt, cdn) {
		if (frm && (frm.is_new() || frm.doc.__islocal)) return;
		var _cdt = cdt || (frm && frm.doctype);
		var _cdn = cdn || (frm && frm.doc && frm.doc.name);
		if (_cdt && _cdn && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, _cdt, _cdn);
		}
		// Calculate chargeable weight when form loads
		if (_cdt && _cdn) {
			var row = locals[_cdt] && locals[_cdt][_cdn] ? locals[_cdt][_cdn] : null;
			if (row && (row.weight || row.volume)) {
				_calculate_package_chargeable_weight(frm, _cdt, _cdn);
			}
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
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	volume: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	weight_uom: function(frm, cdt, cdn) {
		_calculate_package_chargeable_weight(frm, cdt, cdn);
	},
	commodity: function(frm, cdt, cdn) {
		// Populate HS code from commodity's default_hs_code
		let row = locals[cdt][cdn];
		if (row.commodity) {
			frappe.db.get_value('Commodity', row.commodity, 'default_hs_code', (r) => {
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

function _calculate_package_chargeable_weight(frm, cdt, cdn) {
	// Calculate chargeable weight for a package row in the child table
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) return;
	
	if (!row.weight && !row.volume) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight', 0);
		return;
	}
	
	// Get divisor from Sea Freight Settings (convert factor to divisor)
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Sea Freight Settings',
			name: 'Sea Freight Settings',
			fieldname: 'volume_to_weight_factor'
		},
		callback: function(r) {
			var divisor = 1000; // Default (equivalent to 1000 kg/m³ factor)
			if (r && r.message && r.message.volume_to_weight_factor) {
				var factor = parseFloat(r.message.volume_to_weight_factor) || 1000;
				// Convert factor (kg/m³) to divisor: divisor = 1,000,000 / factor
				divisor = 1000000.0 / factor;
			}
			_calculate_and_set_package_chargeable_weight(frm, cdt, cdn, divisor);
		}
	});
}

function _calculate_and_set_package_chargeable_weight(frm, cdt, cdn, divisor) {
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) return;
	
	var volume_weight = 0;
	var chargeable = 0;
	var package_volume = parseFloat(row.volume || 0);
	var package_weight = parseFloat(row.weight || 0);
	
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
	
	frappe.model.set_value(cdt, cdn, 'chargeable_weight', chargeable);
	
	// Set chargeable_weight_uom to match weight_uom if not set
	if (!row.chargeable_weight_uom && row.weight_uom) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight_uom', row.weight_uom);
	}
}
