// Copyright (c) 2025, www.agilasoft.com and contributors
// Child doctype: volume from dimensions via server API (Dimension Volume UOM Conversion).
// Uses Frappe built-in: frappe.model.set_value, refresh_field, frm.trigger.

// Trigger only when focus leaves field (change/blur); no debounce.
function _run_volume_from_dimensions(frm, cdt, cdn) {
	if (!frm || !cdt || !cdn) return;
	_run_volume_from_dimensions_impl(frm, cdt, cdn);
}

function _run_volume_from_dimensions_impl(frm, cdt, cdn) {
	if (!frm || !cdt || !cdn) return;
	var row = frappe.get_doc(cdt, cdn);
	if (!row || row.length === undefined) return;

	var length = parseFloat(row.length || 0);
	var width = parseFloat(row.width || 0);
	var height = parseFloat(row.height || 0);
	var parentfield = row.parentfield || 'packages';

	if (length <= 0 || width <= 0 || height <= 0) {
		frappe.model.set_value(cdt, cdn, 'volume', 0);
		if (typeof refresh_field === 'function') refresh_field('volume', cdn, parentfield);
		frm.trigger('volume', cdt, cdn);
		return;
	}

	var dimension_uom = row.dimension_uom;
	var volume_uom = row.volume_uom;
	var company = frm.doc.company || _get_company_from_form_or_defaults(frm, row);

	if (!dimension_uom || !volume_uom) {
		_fetch_defaults_and_calc_volume(frm, cdt, cdn, length, width, height, dimension_uom, volume_uom, company);
		return;
	}

	_calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn);
}

// Use Frappe built-in refresh_field(fieldname, docname, table_field) for child table cells.
// When grid form ("Editing Row #N") is open, also refresh the grid form's field.
function _refresh_child_field(frm, cdt, cdn, fieldname) {
	var row = frappe.get_doc(cdt, cdn);
	if (!row) return;
	// When grid form is open for this row, refresh its field so user sees updated volume
	var cur = frappe.ui.form.get_cur_frm && frappe.ui.form.get_cur_frm();
	if (cur && cur.doctype === cdt && cur.doc && cur.doc.name === cdn) {
		cur.refresh_field(fieldname);
	}
	var parentfield = row.parentfield || 'packages';
	var parent_frm = frm && frm.doctype === row.parenttype ? frm : _get_parent_form(cdt, cdn);
	var grid = parent_frm && parent_frm.fields_dict && parent_frm.fields_dict[parentfield] ? parent_frm.fields_dict[parentfield].grid : null;
	if (grid && grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn]) {
		grid.grid_rows_by_docname[cdn].refresh_field(fieldname);
	} else if (typeof refresh_field === 'function' && parent_frm && parent_frm.fields_dict && parent_frm.fields_dict[parentfield]) {
		refresh_field(fieldname, cdn, parentfield);
	} else if (grid && grid.refresh_row) {
		grid.refresh_row(cdn);
	}
}

// Globals for use from parent form scripts (Air Booking, etc.) - use window so document handlers see it
window.logistics_calculate_volume_from_dimensions = _run_volume_from_dimensions;
window.logistics_calculate_volume_from_dimensions_immediate = _run_volume_from_dimensions_impl;
// Also set without window for form handlers that may run in same scope
if (typeof logistics_calculate_volume_from_dimensions === 'undefined') {
	logistics_calculate_volume_from_dimensions = _run_volume_from_dimensions;
}
if (typeof logistics_calculate_volume_from_dimensions_immediate === 'undefined') {
	logistics_calculate_volume_from_dimensions_immediate = _run_volume_from_dimensions_impl;
}

function _fetch_defaults_and_calc_volume(frm, cdt, cdn, length, width, height, dimension_uom, volume_uom, company) {
	frappe.call({
		method: 'logistics.utils.measurements.get_default_uoms_api',
		args: { company: company },
		freeze: false,
		callback: function(r) {
			var def_dim = r && r.message && r.message.dimension ? r.message.dimension : null;
			var def_vol = r && r.message && r.message.volume ? r.message.volume : null;
			var dim_uom = dimension_uom || def_dim;
			var vol_uom = volume_uom || def_vol;
			if (cdt && cdn && !dimension_uom && def_dim) frappe.model.set_value(cdt, cdn, 'dimension_uom', def_dim);
			if (cdt && cdn && !volume_uom && def_vol) frappe.model.set_value(cdt, cdn, 'volume_uom', def_vol);
			if (dim_uom && vol_uom) {
				_calculate_volume_from_dimensions_api(length, width, height, dim_uom, vol_uom, company, frm, cdt, cdn);
			} else {
				frappe.model.set_value(cdt, cdn, 'volume', 0);
				_refresh_child_field(frm, cdt, cdn, 'volume');
				frm.trigger('volume', cdt, cdn);
			}
		},
		error: function() {
			frappe.model.set_value(cdt, cdn, 'volume', 0);
			_refresh_child_field(frm, cdt, cdn, 'volume');
			frm.trigger('volume', cdt, cdn);
		}
	});
}

// Helper function to get company from form or defaults
function _get_company_from_form_or_defaults(frm, doc) {
	// Try to get from parent form's doc if available (for unsaved parents)
	if (frm && frm.doc && frm.doc.company) {
		return frm.doc.company;
	}
	// Try to get from parent form if this is a child table row
	if (frm && frm.doctype === 'Air Booking' && frm.doc && frm.doc.company) {
		return frm.doc.company;
	}
	// Fallback to user default
	try {
		return frappe.defaults.get_user_default("Company");
	} catch (e) {
		return null;
	}
}

// Helper function to get parent form from child table row (works for all package doctypes)
function _get_parent_form(cdt, cdn) {
	if (!cdt || !cdn) return null;

	var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : null;
	if (!row || !row.parent || !row.parenttype) return null;

	var parent_doctype = row.parenttype;
	var parent_name = row.parent;

	// Try to find parent form in open forms
	try {
		var open_forms = frappe.ui.form.get_open_forms();
		for (var form_name in open_forms) {
			var form = open_forms[form_name];
			if (form && form.doctype === parent_doctype && form.doc && form.doc.name === parent_name) {
				return form;
			}
		}
	} catch (e) {
		// get_open_forms might not be available in all Frappe versions
	}

	// Fallback: try current form if it's the parent
	var cur_frm = frappe.ui.form.get_cur_frm();
	if (cur_frm && cur_frm.doctype === parent_doctype && cur_frm.doc && cur_frm.doc.name === parent_name) {
		return cur_frm;
	}

	// Last resort: when grid form is open, cur_frm may be child form; parent might be in page
	if (cur_frm && cur_frm.doctype === cdt && cur_frm.page) {
		var page = cur_frm.page;
		if (page.frm && page.frm.doctype === parent_doctype && page.frm.doc && page.frm.doc.name === parent_name) {
			return page.frm;
		}
	}

	return null;
}

// Helper function to trigger parent aggregation
function _trigger_parent_aggregation(cdt, cdn) {
	if (cdt !== 'Air Booking Packages' || !cdn) return;
	
	var parent_frm = _get_parent_form(cdt, cdn);
	if (!parent_frm || !parent_frm.doc) {
		// Parent form not found, try to trigger via model event as fallback
		frappe.model.trigger('volume', cdt, cdn);
		return;
	}
	
	if (parent_frm.doc.override_volume_weight) return;
	
	// When editing from Air Booking form, the volume event already fired and air_booking.js
	// debounced handler will call the API after 300ms. Skip duplicate immediate call to avoid
	// freeze-message-container (some Frappe versions show freeze on frm.call).
	if (parent_frm.doctype === 'Air Booking') return;
	
	// Fallback for other contexts (e.g. dialog): use frappe.call with freeze: false explicitly
	frappe.call({
		method: 'logistics.air_freight.doctype.air_booking.air_booking.aggregate_volume_from_packages_api',
		args: { doc: parent_frm.doc },
		freeze: false,
		callback: function(r) {
			if (r && !r.exc && r.message && parent_frm.doc) {
				if (r.message.total_volume !== undefined) parent_frm.set_value('total_volume', r.message.total_volume);
				if (r.message.total_weight !== undefined) parent_frm.set_value('total_weight', r.message.total_weight);
				if (r.message.chargeable !== undefined) parent_frm.set_value('chargeable', r.message.chargeable);
			}
		},
		error: function(r) {
			console.debug('Aggregation API call failed (document may be unsaved):', r);
		}
	});
}

// Call server API (Dimension Volume UOM Conversion); set volume with set_value + refresh_field.
function _calculate_volume_from_dimensions_api(length, width, height, dimension_uom, volume_uom, company, frm, cdt, cdn) {
	frappe.call({
		method: "logistics.utils.measurements.calculate_volume_from_dimensions_api",
		args: {
			length: length,
			width: width,
			height: height,
			dimension_uom: dimension_uom,
			volume_uom: volume_uom,
			company: company
		},
		freeze: false,
		callback: function(r) {
			var volume = 0;
			if (r && r.message && !r.message.error) {
				var v = r.message.volume;
				if (v !== undefined && v !== null && !isNaN(parseFloat(v))) {
					volume = parseFloat(v);
				}
			}
			frappe.model.set_value(cdt, cdn, 'volume', volume);
			_refresh_child_field(frm, cdt, cdn, 'volume');
			frm.trigger('volume', cdt, cdn);
		},
		error: function() {
			frappe.model.set_value(cdt, cdn, 'volume', 0);
			_refresh_child_field(frm, cdt, cdn, 'volume');
			frm.trigger('volume', cdt, cdn);
		}
	});
}

// Direct model listeners: catch dimension changes even when form handlers don't fire (e.g. grid form)
var _packages_doctypes_with_volume = [
	'Air Booking Packages', 'Air Shipment Packages', 'Sea Booking Packages',
	'Sea Freight Packages', 'Transport Order Package', 'Transport Job Package'
];
_packages_doctypes_with_volume.forEach(function(cdt) {
	frappe.model.on(cdt, ['length', 'width', 'height', 'dimension_uom', 'volume_uom'], function(fieldname, value, doc, skip_dirty_trigger) {
		if (!doc || !doc.parent || doc.parentfield !== 'packages') return;
		// When grid form ("Editing Row #N") is open, cur_frm is the child form; use parent form
		var frm = cur_frm;
		if (frm && frm.doctype === cdt && frm.doc && frm.doc.name === doc.name) {
			frm = _get_parent_form(cdt, doc.name);
		} else if (frm && (!frm.doc || frm.doc.name !== doc.parent || frm.doctype !== doc.parenttype)) {
			frm = _get_parent_form(cdt, doc.name);
		}
		if (!frm) return;
		if (typeof logistics_calculate_volume_from_dimensions === 'function') {
			logistics_calculate_volume_from_dimensions(frm, doc.doctype, doc.name);
		}
	});
});

// Chargeable weight is computed on parent Air Booking only (from aggregated total_weight and total_volume)
window.logistics_get_parent_form = _get_parent_form;
if (typeof logistics_get_parent_form === 'undefined') {
	logistics_get_parent_form = _get_parent_form;
}
