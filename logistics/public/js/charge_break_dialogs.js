// Copyright (c) 2026, www.agilasoft.com and contributors
// Weight Break and Qty Break dialogs - loaded first for Sales Quote and charge doctypes

(function() {
	"use strict";

	window.open_weight_break_rate_dialog = function(frm, row, record_type) {
		record_type = record_type || "Selling";
		var reference_doctype = row.doctype || "Sales Quote Air Freight";
		var reference_no = row.name;
		if (!reference_no || reference_no === "new" || String(reference_no).startsWith("new-")) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Please save the document first before managing weight breaks."),
				indicator: "orange"
			});
			return;
		}
		frappe.call({
			method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.get_weight_breaks",
			args: {
				reference_doctype: reference_doctype,
				reference_no: reference_no,
				record_type: record_type
			},
			callback: function(r) {
				if (!r.message || !r.message.success) {
					frappe.msgprint({ title: __("Error"), message: __("Could not load weight breaks."), indicator: "red" });
					return;
				}
				var weight_breaks = r.message.weight_breaks || [];
				var currency = (row.currency || row.cost_currency || "USD");
				var break_type_options = [
					{ value: "M (Minimum)", label: __("M (Minimum)") },
					{ value: "N (Normal)", label: __("N (Normal)") },
					{ value: "Q (Quantity Break)", label: __("Q (Quantity Break)") }
				];
				var table_data = weight_breaks.length > 0
					? weight_breaks.map(function(wb) {
							return { rate_type: wb.rate_type || "N (Normal)", weight_break: wb.weight_break, unit_rate: wb.unit_rate, currency: wb.currency || currency };
					  })
					: [{ rate_type: "N (Normal)", weight_break: "", unit_rate: "", currency: currency }];

				var table_html = [
					'<div class="weight-break-dialog-table">',
					'<table class="table table-bordered table-sm">',
					'<thead><tr>',
					'<th>' + __("Break Type") + '</th>',
					'<th>' + __("Weight Break") + '</th>',
					'<th>' + __("Unit Rate") + '</th>',
					'<th>' + __("Currency") + '</th>',
					'<th style="width:40px"></th>',
					'</tr></thead>',
					'<tbody id="weight_break_tbody"></tbody>',
					'</table>',
					'<button type="button" class="btn btn-xs btn-secondary mt-2" id="weight_break_add_row">' + __("Add row") + '</button>',
					'</div>'
				].join("");

				var dialog = new frappe.ui.Dialog({
					title: record_type === "Cost" ? __("Manage Cost Weight Breaks") : __("Manage Selling Weight Breaks"),
					size: "large",
					fields: [
						{ fieldname: "weight_breaks_section", fieldtype: "Section Break", label: __("Weight Breaks") },
						{ fieldname: "weight_breaks_html", fieldtype: "HTML", options: table_html }
					],
					primary_action_label: __("Save"),
					primary_action: function(values) {
						var tbody = dialog.$wrapper.find("#weight_break_tbody");
						var to_save = [];
						tbody.find("tr").each(function() {
							var $row = $(this);
							var rate_type = $row.find("select.rate-type").val() || "N (Normal)";
							var weight_break = parseFloat($row.find("input.weight-break").val()) || 0;
							var unit_rate = parseFloat($row.find("input.unit-rate").val()) || 0;
							var curr = $row.find("input.currency-code").val() || currency;
							if (weight_break || unit_rate) {
								to_save.push({ rate_type: rate_type, weight_break: weight_break, unit_rate: unit_rate, currency: curr });
							}
						});
						frappe.call({
							method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.save_weight_breaks_for_reference",
							args: {
								reference_doctype: reference_doctype,
								reference_no: reference_no,
								weight_breaks: to_save,
								record_type: record_type
							},
							callback: function(save_r) {
								if (save_r.message && save_r.message.success) {
									frappe.show_alert({ message: __("Weight breaks saved"), indicator: "green" });
									dialog.hide();
									if (frm && frm.doc) {
										frappe.call({
											method: "logistics.pricing_center.doctype.sales_quote_weight_break.sales_quote_weight_break.refresh_weight_break_html_fields",
											args: { reference_doctype: reference_doctype, reference_no: reference_no },
											callback: function(refresh_r) {
												if (refresh_r.message && refresh_r.message.success) {
													["air_freight", "sea_freight", "transport", "customs", "charges"].forEach(function(fn) {
														if (frm.fields_dict && frm.fields_dict[fn]) {
															frm.refresh_field(fn);
														}
													});
												}
											}
										});
									}
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: (save_r.message && save_r.message.error) || __("Failed to save weight breaks"),
										indicator: "red"
									});
								}
							}
						});
					}
				});
				dialog.show();

				var render_row = function(wb) {
					var rate_type = wb.rate_type || "N (Normal)";
					var opts = break_type_options.map(function(o) {
						return '<option value="' + frappe.utils.escape_html(o.value) + '"' + (o.value === rate_type ? ' selected' : '') + '>' + frappe.utils.escape_html(o.label) + '</option>';
					}).join("");
					return '<tr>' +
						'<td><select class="form-control form-control-sm rate-type">' + opts + '</select></td>' +
						'<td><input type="number" step="0.001" class="form-control form-control-sm weight-break" value="' + (wb.weight_break != null ? frappe.utils.escape_html(wb.weight_break) : '') + '"></td>' +
						'<td><input type="number" step="0.01" class="form-control form-control-sm unit-rate" value="' + (wb.unit_rate != null ? frappe.utils.escape_html(wb.unit_rate) : '') + '"></td>' +
						'<td><input type="text" class="form-control form-control-sm currency-code" value="' + frappe.utils.escape_html(wb.currency || currency) + '" placeholder="USD"></td>' +
						'<td><button type="button" class="btn btn-xs btn-default btn-remove-row">&times;</button></td>' +
						'</tr>';
				};

				dialog.$wrapper.one("shown.bs.modal", function() {
					var tbody = dialog.$wrapper.find("#weight_break_tbody");
					table_data.forEach(function(wb) { tbody.append(render_row(wb)); });

					dialog.$wrapper.find("#weight_break_add_row").on("click", function() {
						tbody.append(render_row({ rate_type: "N (Normal)", weight_break: "", unit_rate: "", currency: currency }));
					});

					dialog.$wrapper.on("click", ".btn-remove-row", function() {
						$(this).closest("tr").remove();
					});
				});
			}
		});
	};

	window.open_qty_break_rate_dialog = function(frm, row, record_type) {
		record_type = record_type || "Selling";
		var reference_doctype = row.doctype || "Sales Quote Air Freight";
		var reference_no = row.name;
		if (!reference_no || reference_no === "new" || String(reference_no).startsWith("new-")) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Please save the document first before managing qty breaks."),
				indicator: "orange"
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
				var currency = (row.currency || row.cost_currency || "USD");
				var table_data = qty_breaks.length > 0
					? qty_breaks.map(function(qb) {
							return { qty_break: qb.qty_break, unit_rate: qb.unit_rate, currency: qb.currency || currency };
					  })
					: [{ qty_break: "", unit_rate: "", currency: currency }];

				var table_html = [
					'<div class="qty-break-dialog-table">',
					'<table class="table table-bordered table-sm">',
					'<thead><tr>',
					'<th>' + __("Qty Break") + '</th>',
					'<th>' + __("Unit Rate") + '</th>',
					'<th>' + __("Currency") + '</th>',
					'<th style="width:40px"></th>',
					'</tr></thead>',
					'<tbody id="qty_break_tbody"></tbody>',
					'</table>',
					'<button type="button" class="btn btn-xs btn-secondary mt-2" id="qty_break_add_row">' + __("Add row") + '</button>',
					'</div>'
				].join("");

				var dialog = new frappe.ui.Dialog({
					title: record_type === "Cost" ? __("Manage Cost Qty Breaks") : __("Manage Selling Qty Breaks"),
					size: "large",
					fields: [
						{ fieldname: "qty_breaks_section", fieldtype: "Section Break", label: __("Qty Breaks") },
						{ fieldname: "qty_breaks_html", fieldtype: "HTML", options: table_html }
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
								record_type: record_type
							},
							callback: function(save_r) {
								if (save_r.message && save_r.message.success) {
									frappe.show_alert({ message: __("Qty breaks saved"), indicator: "green" });
									dialog.hide();
									if (frm && frm.doc) {
										["charges", "air_freight", "sea_freight", "transport", "customs"].forEach(function(fn) {
											if (frm.fields_dict && frm.fields_dict[fn]) {
												frm.refresh_field(fn);
											}
										});
									}
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: (save_r.message && save_r.message.error) || __("Failed to save qty breaks"),
										indicator: "red"
									});
								}
							}
						});
					}
				});
				dialog.show();

				var render_row = function(qb) {
					return '<tr>' +
						'<td><input type="number" step="0.001" class="form-control form-control-sm qty-break" value="' + (qb.qty_break != null ? frappe.utils.escape_html(qb.qty_break) : '') + '"></td>' +
						'<td><input type="number" step="0.01" class="form-control form-control-sm unit-rate" value="' + (qb.unit_rate != null ? frappe.utils.escape_html(qb.unit_rate) : '') + '"></td>' +
						'<td><input type="text" class="form-control form-control-sm currency-code" value="' + frappe.utils.escape_html(qb.currency || currency) + '" placeholder="USD"></td>' +
						'<td><button type="button" class="btn btn-xs btn-default btn-remove-row">&times;</button></td>' +
						'</tr>';
				};

				dialog.$wrapper.one("shown.bs.modal", function() {
					var tbody = dialog.$wrapper.find("#qty_break_tbody");
					table_data.forEach(function(qb) { tbody.append(render_row(qb)); });

					dialog.$wrapper.find("#qty_break_add_row").on("click", function() {
						tbody.append(render_row({ qty_break: "", unit_rate: "", currency: currency }));
					});

					dialog.$wrapper.on("click", ".btn-remove-row", function() {
						$(this).closest("tr").remove();
					});
				});
			}
		});
	};
})();
