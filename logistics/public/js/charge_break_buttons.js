// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
// Weight Break / Qty Break / Percentage Break: grid toolbar buttons + row buttons → dialogs.
// Child tables are detected via LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS and meta (see charge_break_dialogs.js).

var CHARGE_DOCTYPES_WITH_BREAKS =
	window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS ||
	[].concat(
		["Sea Booking Charges", "Sea Shipment Charges", "Sea Consolidation Charges"],
		["Air Booking Charges", "Air Shipment Charges"],
		["Declaration Charges", "Declaration Order Charges"],
		["Transport Order Charges", "Transport Job Charges"],
		["Special Project Charges"],
		["Sales Quote Charge", "Tariff Charge"],
		["MICE Project Charges", "Exhibit Charges"],
		["Change Request Charge"]
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
	"Special Project",
	"Sales Quote",
	"Tariff",
	"MICE Project",
	"Exhibit",
	"Change Request",
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
		selling_percentage_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_percentage_break_rate_dialog === "function") {
				window.open_percentage_break_rate_dialog(frm, row, "Selling");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Percentage Break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		cost_percentage_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_percentage_break_rate_dialog === "function") {
				window.open_percentage_break_rate_dialog(frm, row, "Cost");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Percentage Break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		selling_unit_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_unit_break_rate_dialog === "function") {
				window.open_unit_break_rate_dialog(frm, row, "Selling");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Unit break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
		cost_unit_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_unit_break_rate_dialog === "function") {
				window.open_unit_break_rate_dialog(frm, row, "Cost");
			} else {
				frappe.msgprint({
					title: __("Error"),
					message: __("Unit break dialog is not loaded. Please refresh the page."),
					indicator: "red",
				});
			}
		},
	};
	frappe.ui.form.on(doctype, handlers);
}

CHARGE_DOCTYPES_WITH_BREAKS.forEach(function(doctype) {
	_register_break_handlers(doctype);
	var unitBreakRecalcEvents = {
		use_unit_breaks: function(frm, cdt, cdn) {
			if (
				window.logistics &&
				logistics.charge_type_cleanup &&
				logistics.charge_type_cleanup.recalculate_charge_row
			) {
				logistics.charge_type_cleanup.recalculate_charge_row(frm, cdt, cdn);
			}
		},
		cost_use_unit_breaks: function(frm, cdt, cdn) {
			if (
				window.logistics &&
				logistics.charge_type_cleanup &&
				logistics.charge_type_cleanup.recalculate_charge_row
			) {
				logistics.charge_type_cleanup.recalculate_charge_row(frm, cdt, cdn);
			}
		},
	};
	frappe.ui.form.on(doctype, unitBreakRecalcEvents);
});

CHARGE_PARENT_DOCTYPES.forEach(function(doctype) {
	frappe.ui.form.on(doctype, {
		refresh: function(frm) {
			_add_break_buttons_to_charge_grid(frm);
		},
	});
});

/** Toolbar default: Selling dialogs unless the child table only defines cost-side break buttons (e.g. Sea Consolidation Charges). */
function _weight_break_side_for_child_doctype(dt) {
	if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
		return "Selling";
	}
	var m = frappe.meta.docfield_map[dt];
	var sw = m.selling_weight_break && m.selling_weight_break.fieldtype === "Button";
	var cw = m.cost_weight_break && m.cost_weight_break.fieldtype === "Button";
	if (cw && !sw) {
		return "Cost";
	}
	return "Selling";
}

function _qty_break_side_for_child_doctype(dt) {
	if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
		return "Selling";
	}
	var m = frappe.meta.docfield_map[dt];
	var sq = m.selling_qty_break && m.selling_qty_break.fieldtype === "Button";
	var cq = m.cost_qty_break && m.cost_qty_break.fieldtype === "Button";
	if (cq && !sq) {
		return "Cost";
	}
	return "Selling";
}

function _percentage_break_side_for_child_doctype(dt) {
	if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
		return "Selling";
	}
	var m = frappe.meta.docfield_map[dt];
	var sp = m.selling_percentage_break && m.selling_percentage_break.fieldtype === "Button";
	var cp = m.cost_percentage_break && m.cost_percentage_break.fieldtype === "Button";
	if (cp && !sp) {
		return "Cost";
	}
	return "Selling";
}

function _unit_break_side_for_child_doctype(dt) {
	if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
		return "Selling";
	}
	var m = frappe.meta.docfield_map[dt];
	var su = m.selling_unit_break && m.selling_unit_break.fieldtype === "Button";
	var cu = m.cost_unit_break && m.cost_unit_break.fieldtype === "Button";
	if (cu && !su) {
		return "Cost";
	}
	return "Selling";
}

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
	if (
		window.logistics_charge_child_doctype_has_percentage_break_buttons &&
		window.logistics_charge_child_doctype_has_percentage_break_buttons(dt)
	) {
		return true;
	}
	if (
		window.logistics_charge_child_doctype_has_unit_break_buttons &&
		window.logistics_charge_child_doctype_has_unit_break_buttons(dt)
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
		var $pb = $custom.find(".btn-percentage-break-mgr");
		var $ub = $custom.find(".btn-unit-break-mgr");
		if ($wb.length && $qb.length && $pb.length && $ub.length) {
			return;
		}
		if (!$wb.length) {
			$wb = $('<button type="button" class="btn btn-xs btn-default btn-weight-break-mgr">' + __("Manage Weight Breaks") + "</button>");
			$wb.on("click", function() {
				var row = _get_selected_charge_row(frm, item.fieldname);
				if (row) {
					var wbSide = _weight_break_side_for_child_doctype(grid.doctype);
					window.open_weight_break_rate_dialog && window.open_weight_break_rate_dialog(frm, row, wbSide);
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
					var qbSide = _qty_break_side_for_child_doctype(grid.doctype);
					window.open_qty_break_rate_dialog && window.open_qty_break_rate_dialog(frm, row, qbSide);
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
		if (!$pb.length) {
			$pb = $(
				'<button type="button" class="btn btn-xs btn-default btn-percentage-break-mgr">' +
					__("Manage Percentage Breaks") +
					"</button>"
			);
			$pb.on("click", function() {
				var row = _get_selected_charge_row(frm, item.fieldname);
				if (row) {
					var pbSide = _percentage_break_side_for_child_doctype(grid.doctype);
					window.open_percentage_break_rate_dialog &&
						window.open_percentage_break_rate_dialog(frm, row, pbSide);
				} else {
					frappe.msgprint({
						title: __("Select Row"),
						message: __("Please select a charge row first (click on the row)."),
						indicator: "orange",
					});
				}
			});
			$custom.append($pb);
		}
		if (!$ub.length) {
			$ub = $(
				'<button type="button" class="btn btn-xs btn-default btn-unit-break-mgr">' +
					__("Manage Unit Breaks") +
					"</button>"
			);
			$ub.on("click", function() {
				var row = _get_selected_charge_row(frm, item.fieldname);
				if (row) {
					var ubSide = _unit_break_side_for_child_doctype(grid.doctype);
					window.open_unit_break_rate_dialog && window.open_unit_break_rate_dialog(frm, row, ubSide);
				} else {
					frappe.msgprint({
						title: __("Select Row"),
						message: __("Please select a charge row first (click on the row)."),
						indicator: "orange",
					});
				}
			});
			$custom.append($ub);
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
