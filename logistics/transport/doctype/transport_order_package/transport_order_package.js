// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).
frappe.ui.form.on('Transport Order Package', {
	refresh: function(frm, cdt, cdn) {
		if (frm && (frm.is_new() || frm.doc.__islocal)) return;
		var _cdt = cdt || (frm && frm.doctype);
		var _cdn = cdn || (frm && frm.doc && frm.doc.name);
		if (_cdt && _cdn && typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, _cdt, _cdn);
		}
		update_dimension_field_labels(frm, _cdt, _cdn);
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
		update_dimension_field_labels(frm, cdt, cdn);
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
		update_dimension_field_labels(frm, cdt, cdn);
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
	}
});

function update_dimension_field_labels(frm, cdt, cdn) {
	if (!frm || !cdt || !cdn) return;
	var doc = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : frappe.get_doc(cdt, cdn);
	var dimension_uom = doc && doc.dimension_uom;
	if (!frm.fields_dict || !frm.fields_dict.packages) return;
	var grid = frm.fields_dict.packages.grid;
	if (!grid) {
		return;
	}
	
	// Get the column definitions from grid meta
	let docfields = [];
	if (grid.meta && grid.meta.fields) {
		docfields = grid.meta.fields;
	} else if (grid.docfields) {
		docfields = grid.docfields;
	}
	
	// Get the column definitions
	const dimension_fields = ['length', 'width', 'height'];
	const original_labels = {
		length: 'Length',
		width: 'Width',
		height: 'Height'
	};
	
	// Update labels for all dimension fields in the grid
	dimension_fields.forEach(function(fieldname) {
		// Find the column in docfields
		const col = docfields.find(function(c) {
			return c.fieldname === fieldname;
		});
		
		if (col) {
			// Store original label if not already stored
			if (!col.original_label) {
				col.original_label = col.label || original_labels[fieldname];
			}
			
			// Update label with UOM if dimension_uom is set
			if (dimension_uom) {
				col.label = `${col.original_label} (${dimension_uom})`;
			} else {
				col.label = col.original_label;
			}
		}
	});
	
	// Refresh the grid to show updated labels
	if (grid.refresh) {
		grid.refresh();
	} else if (grid.grid && grid.grid.refresh) {
		grid.grid.refresh();
	}
}

function _calculate_package_chargeable_weight(frm, cdt, cdn) {
	// Calculate chargeable weight for a package row in the child table
	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row) return;
	
	if (!row.weight && !row.volume) {
		frappe.model.set_value(cdt, cdn, 'chargeable_weight', 0);
		return;
	}
	
	// Get divisor from Transport Settings
	frappe.call({
		method: 'frappe.client.get_value',
		args: {
			doctype: 'Transport Settings',
			name: 'Transport Settings',
			fieldname: 'volume_to_weight_divisor'
		},
		callback: function(r) {
			var divisor = 3000; // Default for road transport
			if (r && r.message && r.message.volume_to_weight_divisor) {
				divisor = parseFloat(r.message.volume_to_weight_divisor) || 3000;
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
