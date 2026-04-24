// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
// Weight Break (inline HTML in grid row) and Qty Break buttons for charge tables - shared by Air Booking Charges,
// Air Shipment Charges, Sea Booking Charges, Sea Shipment Charges, Sea Consolidation Charges, Transport Order Charges,
// Transport Job Charges, Declaration Charges, Declaration Order Charges

var CHARGE_DOCTYPES_WITH_BREAKS =
	window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS || [
		"Air Booking Charges",
		"Air Shipment Charges",
		"Sea Booking Charges",
		"Sea Shipment Charges",
		"Sea Consolidation Charges",
		"Transport Order Charges",
		"Transport Job Charges",
		"Declaration Charges",
		"Declaration Order Charges",
	];

var CHARGE_PARENT_DOCTYPES = [
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Sea Consolidation",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
];

function _row_needs_save_before_breaks(row) {
	if (!row || !row.name) {
		return true;
	}
	if (row.name === "new" || String(row.name).indexOf("new-") === 0) {
		return true;
	}
	return false;
}

function _mount_weight_break_side(frm, row, cdt, cdn, grid_form, fieldname, record_type, currency) {
	if (!grid_form || !grid_form.fields_dict || !grid_form.fields_dict[fieldname]) {
		return;
	}
	var $w = grid_form.fields_dict[fieldname].$wrapper;
	if (!$w || !$w.length) {
		return;
	}
	$w.empty();
	if (_row_needs_save_before_breaks(row)) {
		$w.html(
			'<p class="text-muted small">' +
				__("Please save the document first before editing weight breaks.") +
				"</p>"
		);
		return;
	}
	if (typeof window.logistics_weight_break_editor_markup !== "function") {
		$w.html('<p class="text-danger small">' + __("Weight break editor is not loaded. Please refresh the page.") + "</p>");
		return;
	}
	$w.html(window.logistics_weight_break_editor_markup(true));
	var $root = $w.find(".logistics-wb-editor").first();
	frappe.call({
		method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.get_weight_breaks",
		args: {
			reference_doctype: row.doctype,
			reference_no: row.name,
			record_type: record_type,
		},
		callback: function(r) {
			if (!r.message || !r.message.success) {
				$w.html('<p class="text-danger small">' + __("Could not load weight breaks.") + "</p>");
				return;
			}
			window.logistics_populate_weight_break_editor($root, r.message.weight_breaks || [], currency);
			window.logistics_bind_weight_break_editor_controls($root, currency);
			$root
				.find(".logistics-wb-save")
				.off("click.logisticsWbSave")
				.on("click.logisticsWbSave", function() {
					var to_save = window.logistics_collect_weight_break_rows_from_editor($root, currency);
					window.logistics_save_weight_breaks_for_reference(
						row.doctype,
						row.name,
						record_type,
						to_save,
						frm,
						function(ok) {
							if (ok) {
								window.logistics_mount_inline_weight_breaks(frm, cdt, cdn);
							}
						}
					);
				});
		},
	});
}

window.logistics_mount_inline_weight_breaks = function(frm, cdt, cdn) {
	if (!frm || !cdt || !cdn) {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	var grid_form = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
	if (!grid_form || !grid_form.fields_dict) {
		return;
	}
	var selling_currency = row.currency || row.cost_currency || "USD";
	var cost_currency = row.cost_currency || row.currency || "USD";
	if (row.revenue_calculation_method === "Weight Break") {
		_mount_weight_break_side(frm, row, cdt, cdn, grid_form, "selling_weight_break", "Selling", selling_currency);
	}
	if (row.cost_calculation_method === "Weight Break") {
		_mount_weight_break_side(frm, row, cdt, cdn, grid_form, "cost_weight_break", "Cost", cost_currency);
	}
};

function _register_break_handlers(doctype) {
	var handlers = {
		selling_qty_break: function(frm, cdt, cdn) {
			var row = cdn && cdt ? frappe.get_doc(cdt, cdn) : frm && frm.selected_doc ? frm.selected_doc : null;
			if (!row) {
				return;
			}
			if (typeof window.open_qty_break_rate_dialog === "function") {
				window.open_qty_break_rate_dialog(frm, row, "Selling");
			} else {
				frappe.msgprint({ title: __("Error"), message: __("Qty Break dialog is not loaded. Please refresh the page."), indicator: "red" });
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
				frappe.msgprint({ title: __("Error"), message: __("Qty Break dialog is not loaded. Please refresh the page."), indicator: "red" });
			}
		},
		form_render: function(frm, cdt, cdn) {
			setTimeout(function() {
				window.logistics_mount_inline_weight_breaks(frm, cdt, cdn);
			}, 150);
		},
		revenue_calculation_method: function(frm, cdt, cdn) {
			setTimeout(function() {
				window.logistics_mount_inline_weight_breaks(frm, cdt, cdn);
			}, 200);
		},
		cost_calculation_method: function(frm, cdt, cdn) {
			setTimeout(function() {
				window.logistics_mount_inline_weight_breaks(frm, cdt, cdn);
			}, 200);
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

function _add_break_buttons_to_charge_grid(frm) {
	var charge_fields = [];
	for (var fn in frm.fields_dict) {
		var grid = frm.fields_dict[fn] && frm.fields_dict[fn].grid;
		if (grid && grid.doctype && CHARGE_DOCTYPES_WITH_BREAKS.indexOf(grid.doctype) !== -1) {
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
					frappe.msgprint({ title: __("Select Row"), message: __("Please select a charge row first (click on the row)."), indicator: "orange" });
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
					frappe.msgprint({ title: __("Select Row"), message: __("Please select a charge row first (click on the row)."), indicator: "orange" });
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
