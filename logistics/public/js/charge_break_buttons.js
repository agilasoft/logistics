// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
// Weight Break / Qty Break: grid toolbar buttons + row buttons → dialogs.
// Child tables are detected via LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS and meta (see charge_break_dialogs.js).

var CHARGE_DOCTYPES_WITH_BREAKS =
	window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS ||
	[].concat(
		["Sea Booking Charges", "Sea Shipment Charges", "Sea Consolidation Charges"],
		["Air Booking Charges", "Air Shipment Charges"],
		["Declaration Charges", "Declaration Order Charges"],
		["Transport Order Charges", "Transport Job Charges"]
	);

var CHARGE_PARENT_DOCTYPES = [
	"Air Booking",
	"Air Shipment",
	"Air Consolidation",
	"Sea Booking",
	"Sea Shipment",
	"Sea Consolidation",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
];

function _register_break_handlers(doctype) {
	var handlers = {
		selling_weight_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : null;
			if (!row) {
				return;
			}
			if (typeof window.open_weight_break_rate_dialog === "function") {
				window.open_weight_break_rate_dialog(frm, row, "Selling");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Weight break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		cost_weight_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : null;
			if (!row) {
				return;
			}
			if (typeof window.open_weight_break_rate_dialog === "function") {
				window.open_weight_break_rate_dialog(frm, row, "Cost");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Weight break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		selling_qty_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_qty_break_rate_dialog === "function") {
				window.open_qty_break_rate_dialog(frm, row, "Selling");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Qty Break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		cost_qty_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_qty_break_rate_dialog === "function") {
				window.open_qty_break_rate_dialog(frm, row, "Cost");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Qty Break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
	};
	frappe.ui.form.on(doctype, handlers);
}

CHARGE_DOCTYPES_WITH_BREAKS.forEach(function(doctype) {
	_register_break_handlers(doctype);
});

CHARGE_PARENT_DOCTYPES.forEach(function(doctype) {
	frappe.ui.form.on(doctype, {
		refresh: function(frm) {
			_add_break_buttons_to_charge_grid(frm);
		},
	});
});

function _grid_is_logistics_charge_breaks_table(grid) {
	if (!grid || !grid.doctype) {
		return false;
	}
	var dt = grid.doctype;
	if (CHARGE_DOCTYPES_WITH_BREAKS.indexOf(dt) !== -1) {
		return true;
	}
	if (
		window.logistics_charge_child_doctype_has_weight_break_buttons &&
		window.logistics_charge_child_doctype_has_weight_break_buttons(dt)
	) {
		return true;
	}
	if (
		window.logistics_charge_child_doctype_has_qty_break_buttons &&
		window.logistics_charge_child_doctype_has_qty_break_buttons(dt)
	) {
		return true;
	}
	return false;
}

function _add_break_buttons_to_charge_grid(frm) {
	var charge_fields = [];
	for (var fn in frm.fields_dict) {
		var grid = frm.fields_dict[fn] && frm.fields_dict[fn].grid;
		if (_grid_is_logistics_charge_breaks_table(grid)) {
			charge_fields.push({ fieldname: fn, grid: grid });
		}
	}
	charge_fields.forEach(function(item) {
		var grid = item.grid;
		var $custom = grid.wrapper.find(".grid-custom-buttons");
		if (!$custom.length) {
			return;
		}
		var $wb = $custom.find(".btn-weight-break-mgr");
		var $qb = $custom.find(".btn-qty-break-mgr");
		if ($wb.length && $qb.length) {
			return;
		}
		if (!$wb.length) {
			$wb = $('<button type="button" class="btn btn-xs btn-default btn-weight-break-mgr">' + __("Manage Weight Breaks") + "</button>");
			$wb.on("click", function() {
				var row = _get_selected_charge_row(frm, item.fieldname);
				if (row) {
					window.open_weight_break_rate_dialog && window.open_weight_break_rate_dialog(frm, row, "Selling");
				} else {
					frappe.msgprint({
						title: __("Select Row"),
						message: __("Please select a charge row first (click on the row)."),
						indicator: "orange",
					});
				}
			});
			$custom.append($wb);
		}
		if (!$qb.length) {
			$qb = $('<button type="button" class="btn btn-xs btn-default btn-qty-break-mgr">' + __("Manage Qty Breaks") + "</button>");
			$qb.on("click", function() {
				var row = _get_selected_charge_row(frm, item.fieldname);
				if (row) {
					window.open_qty_break_rate_dialog && window.open_qty_break_rate_dialog(frm, row, "Selling");
				} else {
					frappe.msgprint({
						title: __("Select Row"),
						message: __("Please select a charge row first (click on the row)."),
						indicator: "orange",
					});
				}
			});
			$custom.append($qb);
		}
	});
}

function _get_selected_charge_row(frm, fieldname) {
	var grid = frm.fields_dict[fieldname] && frm.fields_dict[fieldname].grid;
	if (!grid) {
		return null;
	}
	var selected = grid.get_selected_children && grid.get_selected_children();
	if (selected && selected.length) {
		return selected[0];
	}
	var open_row = $(".grid-row-open").data("grid_row");
	if (open_row && open_row.doc) {
		return open_row.doc;
	}
	if (frm.selected_doc) {
		return frm.selected_doc;
	}
	var rows = grid.grid_rows || [];
	if (rows.length) {
		return rows[0].doc;
	}
	return null;
}
