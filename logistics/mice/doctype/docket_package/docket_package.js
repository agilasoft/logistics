// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Docket Package", {
	refresh: function (frm, cdt, cdn) {
		if (frm && (frm.is_new() || frm.doc.__islocal)) return;
		var _cdt = cdt || (frm && frm.doctype);
		var _cdn = cdn || (frm && frm.doc && frm.doc.name);
		if (_cdt && _cdn && typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, _cdt, _cdn);
		}
		_update_dimension_field_labels(frm, _cdt, _cdn);
	},
	length: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_update_dimension_field_labels(frm, cdt, cdn);
	},
	width: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	height: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	dimension_uom: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_update_dimension_field_labels(frm, cdt, cdn);
	},
	volume_uom: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
		_trigger_docket_parent_aggregation(frm);
	},
	no_of_packs: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	quantity: function (frm, cdt, cdn) {
		if (typeof logistics_calculate_volume_from_dimensions === "function") {
			logistics_calculate_volume_from_dimensions(frm, cdt, cdn);
		}
	},
	volume: function (frm, cdt, cdn) {
		_trigger_docket_parent_aggregation(frm);
	},
	weight: function (frm, cdt, cdn) {
		_trigger_docket_parent_aggregation(frm);
	},
	weight_uom: function (frm, cdt, cdn) {
		_trigger_docket_parent_aggregation(frm);
	},
});

function _update_dimension_field_labels(frm, cdt, cdn) {
	if (!frm || !cdt || !cdn) return;
	var doc = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : frappe.get_doc(cdt, cdn);
	var dimension_uom = doc && doc.dimension_uom;
	if (!frm.fields_dict || !frm.fields_dict.packages) return;
	var grid = frm.fields_dict.packages.grid;
	if (!grid) return;

	var docfields = [];
	if (grid.meta && grid.meta.fields) {
		docfields = grid.meta.fields;
	} else if (grid.docfields) {
		docfields = grid.docfields;
	}

	var dimension_fields = ["length", "width", "height"];
	var original_labels = { length: "Length", width: "Width", height: "Height" };

	dimension_fields.forEach(function (fieldname) {
		var col = docfields.find(function (c) {
			return c.fieldname === fieldname;
		});
		if (!col) return;
		if (!col.original_label) {
			col.original_label = col.label || original_labels[fieldname];
		}
		if (dimension_uom) {
			col.label = `${col.original_label} (${dimension_uom})`;
		} else {
			col.label = col.original_label;
		}
	});

	if (grid.refresh) {
		grid.refresh();
	} else if (grid.grid && grid.grid.refresh) {
		grid.grid.refresh();
	}
}

function _trigger_docket_parent_aggregation(frm) {
	if (!frm || frm.doctype !== "Docket") return;
	frm.trigger("aggregate_volume_from_packages");
}
