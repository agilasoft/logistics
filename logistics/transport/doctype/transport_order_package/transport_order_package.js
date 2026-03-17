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
		// Chargeable weight is computed on parent Transport Order
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

// Trigger parent Transport Order aggregation (chargeable weight computed on parent)
function _trigger_parent_aggregation(frm) {
	if (!frm || frm.doctype !== 'Transport Order') return;
	frm.trigger('aggregate_volume_from_packages');
}
