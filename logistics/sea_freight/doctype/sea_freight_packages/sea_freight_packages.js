// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: triggers for volume-from-dimensions (uses global logistics_calculate_volume_from_dimensions).

frappe.ui.form.on('Sea Freight Packages', {
	refresh: function(frm) {
		if (frm.doc && (frm.doc.length || frm.doc.width || frm.doc.height)) {
			var cdt = frm.doctype || 'Sea Freight Packages';
			var cdn = (frm.doc && frm.doc.name) ? frm.doc.name : null;
			if (!cdn) return;
			if (typeof logistics_calculate_volume_from_dimensions === 'function') {
				logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
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
	}
});
