// Copyright (c) 2026, www.agilasoft.com and contributors
// Weight Break and Qty Break dialogs - loaded first for Sales Quote and charge doctypes
// Shared weight-break / qty-break editor markup and dialogs (see charge_break_buttons.js for grid + row buttons).

(function() {
	"use strict";

	/** Sea Freight — booking / shipment / consolidation charge child tables (Weight Break & Qty Break row buttons). */
	window.LOGISTICS_SEA_FREIGHT_CHARGE_DOCTYPES = [
		"Sea Booking Charges",
		"Sea Shipment Charges",
		"Sea Consolidation Charges",
	];
	/** Air Freight — booking & shipment charge child tables. */
	window.LOGISTICS_AIR_FREIGHT_CHARGE_DOCTYPES = ["Air Booking Charges", "Air Shipment Charges"];
	/** Customs — declaration & declaration order charge child tables. */
	window.LOGISTICS_CUSTOMS_CHARGE_DOCTYPES = ["Declaration Charges", "Declaration Order Charges"];
	/** Transport — order & job charge child tables. */
	window.LOGISTICS_TRANSPORT_CHARGE_DOCTYPES = ["Transport Order Charges", "Transport Job Charges"];
	/** Pricing — unified quote charge rows (same break UX as Sea Booking Charges). */
	window.LOGISTICS_PRICING_CHARGE_DOCTYPES = ["Sales Quote Charge"];

	window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS = [].concat(
		window.LOGISTICS_SEA_FREIGHT_CHARGE_DOCTYPES,
		window.LOGISTICS_AIR_FREIGHT_CHARGE_DOCTYPES,
		window.LOGISTICS_CUSTOMS_CHARGE_DOCTYPES,
		window.LOGISTICS_TRANSPORT_CHARGE_DOCTYPES,
		window.LOGISTICS_PRICING_CHARGE_DOCTYPES
	);

	/** Any child DocType that ships freight-style weight-break row buttons (reference → Sales Quote Weight Break). */
	window.logistics_charge_child_doctype_has_weight_break_buttons = function(dt) {
		if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
			return false;
		}
		var m = frappe.meta.docfield_map[dt];
		var sw = m.selling_weight_break;
		var cw = m.cost_weight_break;
		return (sw && sw.fieldtype === "Button") || (cw && cw.fieldtype === "Button");
	};

	/** Same pattern for qty-break row buttons. */
	window.logistics_charge_child_doctype_has_qty_break_buttons = function(dt) {
		if (!dt || !frappe.meta.docfield_map || !frappe.meta.docfield_map[dt]) {
			return false;
		}
		var m = frappe.meta.docfield_map[dt];
		var sq = m.selling_qty_break;
		var cq = m.cost_qty_break;
		return (sq && sq.fieldtype === "Button") || (cq && cq.fieldtype === "Button");
	};

	function _wb_reference_from_row(row) {
		var reference_doctype = row.doctype || (row.parentfield === "charges" ? "Sales Quote Charge" : "Sales Quote Air Freight");
		return { reference_doctype: reference_doctype, reference_no: row.name };
	}

	window.logistics_weight_break_break_type_options = function() {
		return [
			{ value: "M (Minimum)", label: __("M (Minimum)") },
			{ value: "N (Normal)", label: __("N (Normal)") },
			{ value: "Q (Quantity Break)", label: __("Q (Quantity Break)") },
		];
	};

	window.logistics_collect_weight_break_rows_from_editor = function($root, default_currency) {
		var to_save = [];
		var currency = default_currency || "USD";
		$root.find("tbody.logistics-wb-tbody tr").each(function() {
			var $row = $(this);
			var rate_type = $row.find("select.rate-type").val() || "N (Normal)";
			var weight_break = parseFloat($row.find("input.weight-break").val()) || 0;
			var unit_rate = parseFloat($row.find("input.unit-rate").val()) || 0;
			var curr = $row.find("input.currency-code").val() || currency;
			if (weight_break || unit_rate) {
				to_save.push({ rate_type: rate_type, weight_break: weight_break, unit_rate: unit_rate, currency: curr });
			}
		});
		return to_save;
	};

	function _wb_render_row(wb, currency, break_type_options) {
		var rate_type = wb.rate_type || "N (Normal)";
		var opts = break_type_options.map(function(o) {
			return '<option value="' + frappe.utils.escape_html(o.value) + '"' + (o.value === rate_type ? " selected" : "") + ">" + frappe.utils.escape_html(o.label) + "</option>";
		}).join("");
		return (
			"<tr>" +
			'<td><select class="form-control form-control-sm rate-type">' + opts + "</select></td>" +
			'<td><input type="number" step="0.001" class="form-control form-control-sm weight-break" value="' +
			(wb.weight_break != null ? frappe.utils.escape_html(wb.weight_break) : "") +
			'"></td>' +
			'<td><input type="number" step="0.01" class="form-control form-control-sm unit-rate" value="' +
			(wb.unit_rate != null ? frappe.utils.escape_html(wb.unit_rate) : "") +
			'"></td>' +
			'<td><input type="text" class="form-control form-control-sm currency-code" value="' +
			frappe.utils.escape_html(wb.currency || currency) +
			'" placeholder="USD"></td>' +
			'<td><button type="button" class="btn btn-xs btn-default btn-remove-row">&times;</button></td>' +
			"</tr>"
		);
	}

	function _logistics_weight_break_editor_shell_fallback(include_save_button) {
		var save_btn = include_save_button
			? '<button type="button" class="btn btn-xs btn-primary logistics-wb-save mt-2">' + __("Save weight breaks") + "</button>"
			: "";
		return (
			'<div class="logistics-wb-editor">' +
			'<table class="table table-bordered table-sm">' +
			"<thead><tr>" +
			"<th>" + __("Break Type") + "</th>" +
			"<th>" + __("Weight Break") + "</th>" +
			"<th>" + __("Unit Rate") + "</th>" +
			"<th>" + __("Currency") + "</th>" +
			'<th style="width:40px"></th>' +
			"</tr></thead>" +
			'<tbody class="logistics-wb-tbody"></tbody>' +
			"</table>" +
			'<button type="button" class="btn btn-xs btn-secondary mt-2 logistics-wb-add-row">' +
			__("Add row") +
			"</button>" +
			save_btn +
			"</div>"
		);
	}

	window.logistics_fetch_weight_break_editor_shell = function(include_save_button, callback) {
		if (typeof callback !== "function") {
			return;
		}
		var key = include_save_button ? "1" : "0";
		window._logistics_wb_shell_cache = window._logistics_wb_shell_cache || {};
		if (window._logistics_wb_shell_cache[key]) {
			callback(window._logistics_wb_shell_cache[key]);
			return;
		}
		frappe.call({
			method: "logistics.utils.weight_break_editor_html.get_weight_break_editor_shell_html",
			args: { include_save_button: include_save_button ? 1 : 0 },
			callback: function(r) {
				var html =
					r.message && r.message.html
						? r.message.html
						: _logistics_weight_break_editor_shell_fallback(include_save_button);
				window._logistics_wb_shell_cache[key] = html;
				callback(html);
			},
			error: function() {
				callback(_logistics_weight_break_editor_shell_fallback(include_save_button));
			},
		});
	};

	window.logistics_populate_weight_break_editor = function($root, weight_breaks, currency) {
		var break_type_options = window.logistics_weight_break_break_type_options();
		var tbody = $root.find("tbody.logistics-wb-tbody");
		tbody.empty();
		var table_data =
			weight_breaks && weight_breaks.length > 0
				? weight_breaks.map(function(wb) {
						return {
							rate_type: wb.rate_type || "N (Normal)",
							weight_break: wb.weight_break,
							unit_rate: wb.unit_rate,
							currency: wb.currency || currency,
						};
				  })
				: [{ rate_type: "N (Normal)", weight_break: "", unit_rate: "", currency: currency }];
		table_data.forEach(function(wb) {
			tbody.append(_wb_render_row(wb, currency, break_type_options));
		});
	};

	window.logistics_bind_weight_break_editor_controls = function($root, currency) {
		var break_type_options = window.logistics_weight_break_break_type_options();
		$root.find(".logistics-wb-add-row").off("click.logisticsWb").on("click.logisticsWb", function() {
			$root.find("tbody.logistics-wb-tbody").append(
				_wb_render_row({ rate_type: "N (Normal)", weight_break: "", unit_rate: "", currency: currency }, currency, break_type_options)
			);
		});
		$root.off("click.logisticsWb", ".btn-remove-row").on("click.logisticsWb", ".btn-remove-row", function() {
			$(this).closest("tr").remove();
		});
	};

	function _refresh_charge_grids_on_parent(frm) {
		if (!frm || !frm.fields_dict) {
			return;
		}
		var types = window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS || [];
		Object.keys(frm.fields_dict).forEach(function(fn) {
			var grid = frm.fields_dict[fn] && frm.fields_dict[fn].grid;
			if (!grid || !grid.doctype) {
				return;
			}
			var dt = grid.doctype;
			var by_list = types.indexOf(dt) !== -1;
			var by_meta_wb =
				window.logistics_charge_child_doctype_has_weight_break_buttons &&
				window.logistics_charge_child_doctype_has_weight_break_buttons(dt);
			var by_meta_qb =
				window.logistics_charge_child_doctype_has_qty_break_buttons &&
				window.logistics_charge_child_doctype_has_qty_break_buttons(dt);
			if (by_list || by_meta_wb || by_meta_qb) {
				frm.refresh_field(fn);
			}
		});
	}

	window.logistics_save_weight_breaks_for_reference = function(
		reference_doctype,
		reference_no,
		record_type,
		to_save,
		frm,
		callback
	) {
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.save_weight_breaks_for_reference",
			args: {
				reference_doctype: reference_doctype,
				reference_no: reference_no,
				weight_breaks: to_save,
				record_type: record_type,
			},
			callback: function(save_r) {
				if (save_r.message && save_r.message.success) {
					frappe.show_alert({ message: __("Weight breaks saved"), indicator: "green" });
					if (callback) {
						callback(true);
					}
					if (frm && frm.doc) {
						frappe.call({
							method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.refresh_weight_break_html_fields",
							args: { reference_doctype: reference_doctype, reference_no: reference_no },
							callback: function(refresh_r) {
								if (refresh_r.message && refresh_r.message.success) {
									_refresh_charge_grids_on_parent(frm);
								}
							},
						});
					}
				} else {
					frappe.msgprint({
						title: __("Error"),
						message: (save_r.message && save_r.message.error) || __("Failed to save weight breaks"),
						indicator: "red",
					});
					if (callback) {
						callback(false);
					}
				}
			},
		});
	};

	window.open_weight_break_rate_dialog = function(frm, row, record_type) {
		record_type = record_type || "Selling";
		var ref = _wb_reference_from_row(row);
		var reference_doctype = ref.reference_doctype;
		var reference_no = ref.reference_no;
		if (!reference_no || reference_no === "new" || String(reference_no).startsWith("new-")) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Please save the document first before managing weight breaks."),
				indicator: "orange",
			});
			return;
		}
		var currency =
			record_type === "Cost"
				? row.cost_currency || row.currency || "USD"
				: row.currency || row.cost_currency || "USD";
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.get_weight_breaks",
			args: {
				reference_doctype: reference_doctype,
				reference_no: reference_no,
				record_type: record_type,
			},
			callback: function(r) {
				if (!r.message || !r.message.success) {
					frappe.msgprint({ title: __("Error"), message: __("Could not load weight breaks."), indicator: "red" });
					return;
				}
				var weight_breaks = r.message.weight_breaks || [];
				window.logistics_fetch_weight_break_editor_shell(false, function(table_html) {
					var dialog = new frappe.ui.Dialog({
						title: record_type === "Cost" ? __("Manage Cost Weight Breaks") : __("Manage Selling Weight Breaks"),
						size: "large",
						fields: [
							{ fieldname: "weight_breaks_section", fieldtype: "Section Break", label: __("Weight Breaks") },
							{ fieldname: "weight_breaks_html", fieldtype: "HTML", options: table_html },
						],
						primary_action_label: __("Save"),
						primary_action: function() {
							var $root = dialog.$wrapper.find(".logistics-wb-editor").first();
							var to_save = window.logistics_collect_weight_break_rows_from_editor($root, currency);
							window.logistics_save_weight_breaks_for_reference(
								reference_doctype,
								reference_no,
								record_type,
								to_save,
								frm,
								function(ok) {
									if (ok) {
										dialog.hide();
									}
								}
							);
						},
					});
					dialog.show();

					dialog.$wrapper.one("shown.bs.modal", function() {
						var $html_field =
							dialog.fields_dict.weight_breaks_html && dialog.fields_dict.weight_breaks_html.$wrapper;
						var $root = $html_field
							? $html_field.find(".logistics-wb-editor").first()
							: dialog.$wrapper.find(".logistics-wb-editor").first();
						window.logistics_populate_weight_break_editor($root, weight_breaks, currency);
						window.logistics_bind_weight_break_editor_controls($root, currency);
					});
				});
			},
		});
	};

	window.open_qty_break_rate_dialog = function(frm, row, record_type) {
		record_type = record_type || "Selling";
		var reference_doctype = row.doctype || (row.parentfield === "charges" ? "Sales Quote Charge" : "Sales Quote Air Freight");
		var reference_no = row.name;
		if (!reference_no || reference_no === "new" || String(reference_no).startsWith("new-")) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Please save the document first before managing qty breaks."),
				indicator: "orange",
			});
			return;
		}
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote_qty_break.sales_quote_qty_break.get_qty_breaks",
			args: { reference_doctype: reference_doctype, reference_no: reference_no, record_type: record_type },
			callback: function(r) {
				if (!r.message || !r.message.success) {
					frappe.msgprint({ title: __("Error"), message: __("Could not load qty breaks."), indicator: "red" });
					return;
				}
				var qty_breaks = r.message.qty_breaks || [];
				var currency = row.currency || row.cost_currency || "USD";
				var table_data =
					qty_breaks.length > 0
						? qty_breaks.map(function(qb) {
								return { qty_break: qb.qty_break, unit_rate: qb.unit_rate, currency: qb.currency || currency };
						  })
						: [{ qty_break: "", unit_rate: "", currency: currency }];

				var table_html = [
					'<div class="qty-break-dialog-table">',
					'<table class="table table-bordered table-sm">',
					"<thead><tr>",
					"<th>" + __("Qty Break") + "</th>",
					"<th>" + __("Unit Rate") + "</th>",
					"<th>" + __("Currency") + "</th>",
					'<th style="width:40px"></th>',
					"</tr></thead>",
					'<tbody id="qty_break_tbody"></tbody>',
					"</table>",
					'<button type="button" class="btn btn-xs btn-secondary mt-2" id="qty_break_add_row">' + __("Add row") + "</button>",
					"</div>",
				].join("");

				var dialog = new frappe.ui.Dialog({
					title: record_type === "Cost" ? __("Manage Cost Qty Breaks") : __("Manage Selling Qty Breaks"),
					size: "large",
					fields: [
						{ fieldname: "qty_breaks_section", fieldtype: "Section Break", label: __("Qty Breaks") },
						{ fieldname: "qty_breaks_html", fieldtype: "HTML", options: table_html },
					],
					primary_action_label: __("Save"),
					primary_action: function(values) {
						var tbody = dialog.$wrapper.find("#qty_break_tbody");
						var to_save = [];
						tbody.find("tr").each(function() {
							var $row = $(this);
							var qty_break = parseFloat($row.find("input.qty-break").val()) || 0;
							var unit_rate = parseFloat($row.find("input.unit-rate").val()) || 0;
							var curr = $row.find("input.currency-code").val() || currency;
							if (qty_break || unit_rate) {
								to_save.push({ qty_break: qty_break, unit_rate: unit_rate, currency: curr });
							}
						});
						frappe.call({
							method: "logistics.pricing_center.doctype.sales_quote_qty_break.sales_quote_qty_break.save_qty_breaks_for_reference",
							args: {
								reference_doctype: reference_doctype,
								reference_no: reference_no,
								qty_breaks: to_save,
								record_type: record_type,
							},
							callback: function(save_r) {
								if (save_r.message && save_r.message.success) {
									frappe.show_alert({ message: __("Qty breaks saved"), indicator: "green" });
									dialog.hide();
									if (frm && frm.doc) {
										_refresh_charge_grids_on_parent(frm);
									}
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: (save_r.message && save_r.message.error) || __("Failed to save qty breaks"),
										indicator: "red",
									});
								}
							},
						});
					},
				});
				dialog.show();

				var render_row = function(qb) {
					return (
						"<tr>" +
						'<td><input type="number" step="0.001" class="form-control form-control-sm qty-break" value="' +
						(qb.qty_break != null ? frappe.utils.escape_html(qb.qty_break) : "") +
						'"></td>' +
						'<td><input type="number" step="0.01" class="form-control form-control-sm unit-rate" value="' +
						(qb.unit_rate != null ? frappe.utils.escape_html(qb.unit_rate) : "") +
						'"></td>' +
						'<td><input type="text" class="form-control form-control-sm currency-code" value="' +
						frappe.utils.escape_html(qb.currency || currency) +
						'" placeholder="USD"></td>' +
						'<td><button type="button" class="btn btn-xs btn-default btn-remove-row">&times;</button></td>' +
						"</tr>"
					);
				};

				dialog.$wrapper.one("shown.bs.modal", function() {
					var tbody = dialog.$wrapper.find("#qty_break_tbody");
					table_data.forEach(function(qb) {
						tbody.append(render_row(qb));
					});

					dialog.$wrapper.find("#qty_break_add_row").on("click", function() {
						tbody.append(render_row({ qty_break: "", unit_rate: "", currency: currency }));
					});

					dialog.$wrapper.on("click", ".btn-remove-row", function() {
						$(this).closest("tr").remove();
					});
				});
			},
		});
	};

	// Grid row "Weight Break" buttons: ControlButton only triggers frappe.ui.form.on when
	// script_manager.has_handlers(...) is true; in expanded child row forms that path is unreliable.
	// Capture on document so we open the dialog before the event reaches the inner <button>.
	/**
	 * Calculation Method drives depends_on for Weight Break / Qty Break Button fields above it in field_order.
	 * Re-run layout dependency when it changes (grid_form.refresh_field can skip layout.refresh_dependency in some cases).
	 */
	(function _logistics_register_charge_calc_method_break_visibility() {
		if (window.__logistics_charge_calc_method_visibility_hooks) {
			return;
		}
		window.__logistics_charge_calc_method_visibility_hooks = true;

		function _logistics_child_row_calc_visibility_hook_rows() {
			var freight = window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS || [];
			var rows = [];
			freight.forEach(function(dt) {
				rows.push({ doctype: dt, fields: ["revenue_calculation_method", "cost_calculation_method"] });
			});
			if (freight.indexOf("Sales Quote Charge") === -1) {
				rows.push({
					doctype: "Sales Quote Charge",
					fields: ["revenue_calculation_method", "cost_calculation_method"],
				});
			}
			rows.push(
				{
					doctype: "Sales Quote Air Freight",
					fields: ["calculation_method", "cost_calculation_method"],
				},
				{
					doctype: "Sales Quote Sea Freight",
					fields: ["calculation_method", "cost_calculation_method"],
				},
				{
					doctype: "Warehouse Contract Item",
					fields: [
						"calculation_method",
						"unit_type",
						"volume_calculation_method",
						"storage_charge",
						"inbound_charge",
						"outbound_charge",
						"transfer_charge",
						"vas_charge",
						"stocktake_charge",
						"billing_method",
					],
				}
			);
			return rows;
		}

		function deferRefreshChargeBreakDepends(doc) {
			var name = doc && doc.name;
			if (!name) {
				return;
			}
			setTimeout(function() {
				var gridRow =
					typeof frappe.ui.form.get_open_grid_form === "function" &&
					frappe.ui.form.get_open_grid_form();
				if (!gridRow || !gridRow.doc || gridRow.doc.name !== name) {
					return;
				}
				if (gridRow.grid_form && gridRow.grid_form.layout) {
					gridRow.grid_form.layout.refresh_dependency();
					gridRow.grid_form.layout.refresh_sections();
				}
				if (typeof gridRow.refresh_dependency === "function") {
					gridRow.refresh_dependency();
				}
			}, 0);
		}
		function attachCalcMethodHooks(dt, fieldnames) {
			if (!dt || !fieldnames || !fieldnames.length) {
				return;
			}
			fieldnames.forEach(function(fname) {
				frappe.model.on(dt, fname, function(fieldname, value, doc) {
					deferRefreshChargeBreakDepends(doc);
				});
			});
		}
		_logistics_child_row_calc_visibility_hook_rows().forEach(function(row) {
			attachCalcMethodHooks(row.doctype, row.fields);
		});
	})();

	(function _logistics_install_charge_break_row_button_click_capture() {
		if (window.__logistics_charge_break_row_button_capture_installed) {
			return;
		}
		window.__logistics_charge_break_row_button_capture_installed = true;
		document.addEventListener(
			"click",
			function(ev) {
				var t = ev.target;
				if (!t || String(t.tagName || "").toUpperCase() !== "BUTTON") {
					return;
				}
				if (!t.closest || !t.closest(".form-in-grid")) {
					return;
				}
				var wrap = t.closest(".frappe-control[data-fieldname]");
				if (!wrap || !wrap.fieldobj) {
					return;
				}
				var fo = wrap.fieldobj;
				var fn = fo.df && fo.df.fieldname;
				if (!fo.frm || !fo.docname) {
					return;
				}
				var row = frappe.get_doc(fo.doctype, fo.docname);
				if (!row) {
					return;
				}
				if (fn === "selling_weight_break" || fn === "cost_weight_break") {
					var known_wb = (window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS || []).indexOf(fo.doctype) !== -1;
					var meta_wb =
						window.logistics_charge_child_doctype_has_weight_break_buttons &&
						window.logistics_charge_child_doctype_has_weight_break_buttons(fo.doctype);
					if (!known_wb && !meta_wb) {
						return;
					}
					if (typeof window.open_weight_break_rate_dialog !== "function") {
						return;
					}
					ev.preventDefault();
					ev.stopPropagation();
					ev.stopImmediatePropagation();
					window.open_weight_break_rate_dialog(fo.frm, row, fn === "cost_weight_break" ? "Cost" : "Selling");
					return;
				}
				if (fn === "selling_qty_break" || fn === "cost_qty_break") {
					var known_qb = (window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS || []).indexOf(fo.doctype) !== -1;
					var meta_qb =
						window.logistics_charge_child_doctype_has_qty_break_buttons &&
						window.logistics_charge_child_doctype_has_qty_break_buttons(fo.doctype);
					if (!known_qb && !meta_qb) {
						return;
					}
					if (typeof window.open_qty_break_rate_dialog !== "function") {
						return;
					}
					ev.preventDefault();
					ev.stopPropagation();
					ev.stopImmediatePropagation();
					window.open_qty_break_rate_dialog(fo.frm, row, fn === "cost_qty_break" ? "Cost" : "Selling");
				}
			},
			true
		);
	})();
})();
