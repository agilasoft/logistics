// Copyright (c) 2026, AgilaSoft and contributors
// Blanket Quotation call-off dialog (parent header + selectable charge rows)

frappe.provide("logistics");

var BCO_SERVICE_ICONS = {
	Sea: "fa-ship",
	Air: "fa-plane",
	Transport: "fa-truck",
	Customs: "fa-file-text-o",
	Warehousing: "fa-archive",
};

logistics.open_blanket_call_off_flow = function (frm) {
	if (!frm || !frm.doc || frm.doc.__islocal || frm.doc.docstatus !== 1) {
		frappe.msgprint(__("Save and submit the Sales Quote first."));
		return;
	}
	if (frm.doc.quotation_type !== "Regular" || !frm.doc.blanket_quotation) {
		frappe.msgprint(__("Call-off is only available for submitted Regular Blanket Quotations."));
		return;
	}

	frappe.call({
		method: "logistics.utils.blanket_call_off.get_blanket_call_off_target_options",
		args: { sales_quote: frm.doc.name },
		callback: function (r) {
			var targets = (r.message && r.message.targets) || [];
			if (!targets.length) {
				frappe.msgprint(__("No charge lines on this quote support a call-off target."));
				return;
			}
			logistics.open_blanket_call_off_dialog(frm, targets[0], targets);
		},
	});
};

logistics.open_blanket_call_off_dialog = function (frm, target_doctype, available_targets) {
	frappe.call({
		method: "logistics.utils.blanket_call_off.preview_blanket_call_off",
		args: { sales_quote: frm.doc.name, target_doctype: target_doctype },
		freeze: true,
		freeze_message: __("Loading call-off…"),
		callback: function (r) {
			if (!r || r.exc || !r.message) {
				frappe.msgprint(__("Could not load call-off preview."));
				return;
			}
			if (available_targets && available_targets.length) {
				r.message.available_targets = available_targets;
			}
			_bco_show_dialog(frm, r.message);
		},
	});
};

function _bco_format_date(val) {
	if (!val) return "";
	return frappe.datetime.str_to_user(val);
}

function _bco_service_icon(service) {
	var key = (service || "").trim();
	var cls = BCO_SERVICE_ICONS[key] || "fa-cube";
	return '<span class="bco-service-icon"><i class="fa ' + cls + '"></i></span>';
}

function _bco_quote_header_html(meta) {
	if (!meta) return "";
	var validParts = [];
	if (meta.valid_from) validParts.push(_bco_format_date(meta.valid_from));
	if (meta.valid_until) validParts.push(_bco_format_date(meta.valid_until));
	var validText = validParts.length ? validParts.join(" " + __("to") + " ") : "—";
	return (
		'<div class="bco-quote-header">' +
		'<div class="bco-quote-header-row">' +
		'<span class="bco-quote-label">' +
		__("Source Quote") +
		":</span> " +
		'<strong class="bco-quote-name">' +
		frappe.utils.escape_html(meta.name || "") +
		"</strong> " +
		'<span class="indicator-pill green">' +
		frappe.utils.escape_html(meta.status || __("Submitted")) +
		"</span> " +
		'<span class="bco-quote-valid text-muted">' +
		frappe.utils.escape_html(validText) +
		"</span>" +
		"</div>" +
		'<p class="bco-quote-hint text-muted">' +
		__("Review and edit header fields. Optionally narrow to match the shipment being released.") +
		"</p>" +
		"</div>"
	);
}

function _bco_detail_panel_html(row) {
	var sum = row.summary || {};
	var desc = sum.description || sum.item_name || "—";
	var rate = row.rate_display || "—";
	var calc = row.calculation_method || "—";
	var costSide = row.cost_side || "—";
	var billTo = row.bill_to || "—";
	var payTo = row.pay_to || "—";
	return (
		'<div class="bco-detail-panel">' +
		'<div class="bco-detail-grid">' +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Description") +
		"</span><span>" +
		frappe.utils.escape_html(desc) +
		"</span></div>" +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Rate") +
		"</span><span>" +
		frappe.utils.escape_html(rate) +
		"</span></div>" +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Calculation Method") +
		"</span><span>" +
		frappe.utils.escape_html(calc) +
		"</span></div>" +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Cost Side") +
		"</span><span>" +
		frappe.utils.escape_html(costSide) +
		"</span></div>" +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Bill To") +
		"</span><span>" +
		frappe.utils.escape_html(billTo) +
		"</span></div>" +
		'<div class="bco-detail-item"><span class="bco-detail-label">' +
		__("Pay To") +
		"</span><span>" +
		frappe.utils.escape_html(payTo) +
		"</span></div>" +
		"</div></div>"
	);
}

function _bco_row_matches_parent_filter(row, parentValues, narrow) {
	if (!narrow) return true;
	var sum = row.summary || {};
	var checks = [
		["origin_port", sum.origin_port],
		["destination_port", sum.destination_port],
		["shipping_line", sum.shipping_line],
		["airline", sum.airline],
		["location_from", sum.location_from],
		["location_to", sum.location_to],
		["customs_authority", sum.customs_authority],
		["declaration_type", sum.declaration_type],
		["customs_broker", sum.customs_broker],
	];
	for (var i = 0; i < checks.length; i++) {
		var filterVal = parentValues[checks[i][0]];
		if (!filterVal || !String(filterVal).trim()) continue;
		var rowVal = checks[i][1];
		// Blank on the charge row = wildcard; only exclude explicit mismatches.
		if (rowVal && String(rowVal).trim() && String(rowVal).trim() !== String(filterVal).trim()) {
			return false;
		}
	}
	return true;
}

function _bco_bind_control_change(control, handler) {
	if (!control) return;
	if (control.$input && control.$input.length) {
		control.$input.on("change", handler);
		return;
	}
	if (control.$wrapper) {
		control.$wrapper.on("change", "input, select, textarea", handler);
	}
}

function _bco_mount_readonly_field(col, spec, value) {
	col.append($('<label class="logistics-gcfq-filter-label">').text(spec.label));
	var $inp = $(
		'<input type="text" class="form-control input-sm logistics-gcfq-filter-input" readonly tabindex="-1">'
	).val(value || "");
	col.append($inp);
	return {
		spec: spec,
		read_only: true,
		get_value: function () {
			return value || "";
		},
		set_value: function (v) {
			value = v || "";
			$inp.val(value);
		},
	};
}

function _bco_show_dialog(frm, preview) {
	var parentDefaults = Object.assign({}, preview.parent_defaults || {});
	var parentValues = Object.assign({}, parentDefaults);
	var chargeRows = preview.charge_rows || [];
	var narrowToShipment = false;
	var state = {
		frm: frm,
		preview: preview,
		parentDefaults: parentDefaults,
		parentValues: parentValues,
		chargeRows: chargeRows,
		narrowToShipment: narrowToShipment,
		controls: [],
		targetControl: null,
		renderChargeTable: null,
	};

	var d = new frappe.ui.Dialog({
		title: __("Create Call-Off – New Booking from Blanket Quote"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "bco_body",
				options: '<div class="bco-dialog-body"></div>',
			},
		],
		primary_action_label: __("Confirm & Create"),
		primary_action: function () {
			_bco_confirm_create(state, d);
		},
		secondary_action_label: __("Cancel"),
		secondary_action: function () {
			d.hide();
		},
	});

	d.$wrapper.addClass("logistics-gcfq-dialog logistics-bco-dialog");
	d.show();

	var $body = d.$wrapper.find(".bco-dialog-body");
	$body.append(
		'<div class="bco-quote-header-mount"></div>' +
			'<div class="bco-parent-area"></div>' +
			'<div class="bco-charges-area"></div>'
	);

	$body.find(".bco-quote-header-mount").html(_bco_quote_header_html(preview.quote_meta));

	var $parent = $body.find(".bco-parent-area");
	$parent.append(
		'<div class="bco-section">' +
			'<div class="bco-section-head">' +
			'<div class="bco-section-title">' +
			__("Parent Filter") +
			"</div>" +
			'<div class="bco-section-subtitle text-muted">' +
			__("Header to be written to new document") +
			"</div>" +
			"</div>" +
			'<div class="bco-parent-toolbar">' +
			'<button type="button" class="btn btn-xs btn-default bco-reset-filters">' +
			__("Reset Filters") +
			"</button>" +
			'<label class="bco-narrow-toggle">' +
			'<input type="checkbox" class="bco-narrow-cb" /> ' +
			__("Narrow to this shipment") +
			"</label>" +
			"</div>" +
			'<div class="logistics-gcfq-filters-grid bco-parent-grid"></div>' +
			'<p class="bco-section-footnote text-muted">' +
			__("These fields will be written to the new document.") +
			"</p>" +
			"</div>"
	);

	var $chargesWrap = $body.find(".bco-charges-area");
	$chargesWrap.append(
		'<div class="bco-section bco-charges-section">' +
			'<div class="bco-section-head bco-charges-head">' +
			'<div>' +
			'<div class="bco-section-title">' +
			__("Quote Charge Lines") +
			"</div>" +
			'<div class="bco-section-subtitle text-muted">' +
			__("Select only applicable lines for this call-off") +
			"</div>" +
			"</div>" +
			'<div class="bco-charges-toolbar">' +
			'<span class="bco-selection-count"></span> ' +
			'<button type="button" class="btn btn-xs btn-default bco-select-all">' +
			__("Select All") +
			"</button>" +
			"</div>" +
			"</div>" +
			'<div class="logistics-gcfq-table-wrap bco-charges-table-wrap">' +
			'<table class="logistics-gcfq-table bco-charges-table">' +
			"<thead><tr>" +
			'<th class="bco-col-check"></th>' +
			'<th class="bco-col-icon"></th>' +
			"<th>" +
			__("Service Type") +
			"</th>" +
			"<th>" +
			__("Charge Group") +
			"</th>" +
			"<th>" +
			__("Item Code") +
			"</th>" +
			"<th>" +
			__("Routing (Summary)") +
			"</th>" +
			"<th>" +
			__("Calculation Method") +
			"</th>" +
			"<th>" +
			__("Cost Side") +
			"</th>" +
			"<th>" +
			__("Bill To / Pay To") +
			"</th>" +
			'<th class="bco-col-expand"></th>' +
			"</tr></thead>" +
			'<tbody class="bco-charge-tbody"></tbody>' +
			"</table></div>" +
			'<p class="bco-section-footnote text-muted">' +
			__("Expand a row to view full commercial details. Select only the charge lines applicable to this call-off.") +
			"</p>" +
			"</div>"
	);

	var $grid = $parent.find(".bco-parent-grid");
	var $tbody = $chargesWrap.find(".bco-charge-tbody");
	var selectedNames = {};

	function updateSelectionCount() {
		var eligible = $tbody.find("tr.bco-charge-row:not(.bco-charge-row--disabled)");
		var selected = eligible.find(".bco-charge-cb:checked").length;
		var total = eligible.length;
		$chargesWrap.find(".bco-selection-count").text(__("{0} of {1} selected", [selected, total]));
	}

	function renderChargeTable() {
		$tbody.empty();
		var visibleEligible = 0;
		chargeRows.forEach(function (row) {
			var matchesFilter = _bco_row_matches_parent_filter(row, parentValues, narrowToShipment);
			if (matchesFilter) {
				visibleEligible += 1;
			}

			var sum = row.summary || {};
			var service = sum.service_type || "";
			var billPay = (row.bill_to || "—") + (row.pay_to ? " / " + row.pay_to : "");
			var checked = selectedNames[row.name] ? " checked" : "";
			var disabled = !matchesFilter;
			var rowClass =
				"bco-charge-row" +
				(disabled ? " bco-charge-row--disabled text-muted" : "") +
				(!row.matches_target ? " bco-charge-row--other-service" : "");
			var $tr = $(
				'<tr class="' +
					rowClass +
					'" data-name="' +
					frappe.utils.escape_html(row.name) +
					'">' +
					'<td class="bco-col-check"><input type="checkbox" class="bco-charge-cb"' +
					checked +
					(disabled ? " disabled" : "") +
					" /></td>" +
					'<td class="bco-col-icon">' +
					_bco_service_icon(service) +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(service) +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(sum.charge_group || "—") +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(sum.item_code || "—") +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(row.routing_summary || "—") +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(row.calculation_method || "—") +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(row.cost_side || "—") +
					"</td>" +
					"<td>" +
					frappe.utils.escape_html(billPay) +
					"</td>" +
					'<td class="bco-col-expand"><button type="button" class="btn btn-xs btn-link bco-toggle-detail"><i class="fa fa-chevron-down"></i></button></td>' +
					"</tr>"
			);
			var $detailTr = $(
				'<tr class="bco-charge-detail-row" data-name="' +
					frappe.utils.escape_html(row.name) +
					'" style="display:none"><td colspan="10">' +
					_bco_detail_panel_html(row) +
					"</td></tr>"
			);
			$tr.find(".bco-charge-cb").on("change", function () {
				if (disabled) {
					this.checked = false;
					return;
				}
				if (this.checked) {
					selectedNames[row.name] = true;
					_bco_sync_parent_from_row(state.controls, parentValues, sum);
				} else {
					delete selectedNames[row.name];
				}
				updateSelectionCount();
			});
			$tr.find(".bco-toggle-detail").on("click", function (e) {
				e.preventDefault();
				var open = $detailTr.is(":visible");
				$detailTr.toggle(!open);
				$(this).find("i").toggleClass("fa-chevron-down", open).toggleClass("fa-chevron-up", !open);
			});
			$tbody.append($tr).append($detailTr);
		});
		updateSelectionCount();
		if (!visibleEligible && chargeRows.length) {
			$chargesWrap.find(".bco-charges-empty-hint").remove();
			$chargesWrap.find(".bco-charges-table-wrap").after(
				'<p class="bco-charges-empty-hint text-muted">' +
					__("No eligible charge lines match the current filters. Turn off “Narrow to this shipment” or change Document Type.") +
					"</p>"
			);
		} else {
			$chargesWrap.find(".bco-charges-empty-hint").remove();
		}
	}

	state.renderChargeTable = renderChargeTable;
	renderChargeTable();

	function buildParentFields() {
		state.controls = [];
		$grid.empty();

		var targets = preview.available_targets || [preview.target_doctype];
		var targetCol = $('<div class="logistics-gcfq-filter-cell">').appendTo($grid);
		targetCol.append($('<label class="logistics-gcfq-filter-label">').text(__("Document Type")));
		var targetControl = frappe.ui.form.make_control({
			df: {
				fieldtype: "Select",
				fieldname: "target_doctype",
				options: targets.join("\n"),
				default: preview.target_doctype,
			},
			parent: targetCol,
			render_input: true,
		});
		targetControl.set_value(preview.target_doctype);
		_bco_bind_control_change(targetControl, function () {
			var newTarget = targetControl.get_value();
			if (!newTarget || newTarget === state.preview.target_doctype) return;
			frappe.call({
				method: "logistics.utils.blanket_call_off.preview_blanket_call_off",
				args: { sales_quote: frm.doc.name, target_doctype: newTarget },
				freeze: true,
				freeze_message: __("Loading call-off…"),
				callback: function (r) {
					if (!r || r.exc || !r.message) {
						frappe.msgprint(__("Could not load call-off preview."));
						targetControl.set_value(state.preview.target_doctype);
						return;
					}
					r.message.available_targets = targets;
					d.hide();
					_bco_show_dialog(frm, r.message);
				},
			});
		});
		state.targetControl = targetControl;

		(preview.parent_field_specs || []).forEach(function (spec) {
			var col = $('<div class="logistics-gcfq-filter-cell">').appendTo($grid);
			var labelText = spec.label + (spec.reqd ? " *" : "");
			col.append($('<label class="logistics-gcfq-filter-label">').text(labelText));

			if (spec.read_only) {
				var ro = _bco_mount_readonly_field(col, spec, parentValues[spec.fieldname] || "");
				state.controls.push(ro);
				return;
			}

			if (spec.filter_only && spec.fieldtype === "Data") {
				col.append($('<label class="logistics-gcfq-filter-label">').text(labelText));
				var $filterInp = $(
					'<input type="text" class="form-control input-sm logistics-gcfq-filter-input bco-filter-only-input">'
				).val(parentValues[spec.fieldname] || "");
				col.append($filterInp);
				$filterInp.on("change input", function () {
					parentValues[spec.fieldname] = $(this).val();
					renderChargeTable();
				});
				state.controls.push({
					spec: spec,
					filter_only: true,
					get_value: function () {
						return $filterInp.val();
					},
					set_value: function (v) {
						$filterInp.val(v || "");
					},
				});
				return;
			}

			var df = {
				fieldtype: spec.fieldtype,
				fieldname: spec.fieldname,
				label: spec.label,
				options: spec.options,
				default: parentValues[spec.fieldname] || "",
				reqd: spec.reqd ? 1 : 0,
			};
			if (spec.fieldtype === "Dynamic Link") {
				df.get_options = function () {
					return parentValues.location_type || "UNLOCO";
				};
			}
			var control = frappe.ui.form.make_control({
				df: df,
				parent: col,
				render_input: true,
			});
			control.set_value(parentValues[spec.fieldname] || "");
			_bco_bind_control_change(control, function () {
				parentValues[spec.fieldname] = control.get_value();
				renderChargeTable();
			});
			state.controls.push({ spec: spec, control: control });
		});
	}

	try {
		buildParentFields();
	} catch (e) {
		console.error("[blanket call-off] parent filter fields failed", e);
		frappe.show_alert({
			message: __("Some header fields could not load. Charge lines are still available below."),
			indicator: "orange",
		});
	}

	$parent.find(".bco-reset-filters").on("click", function () {
		Object.keys(parentValues).forEach(function (k) {
			delete parentValues[k];
		});
		Object.assign(parentValues, parentDefaults);
		state.controls.forEach(function (c) {
			if (c.read_only || c.filter_only) {
				c.set_value(parentValues[c.spec.fieldname] || "");
			} else if (c.control) {
				c.control.set_value(parentValues[c.spec.fieldname] || "");
			}
		});
		renderChargeTable();
	});

	$parent.find(".bco-narrow-cb").on("change", function () {
		narrowToShipment = this.checked;
		state.narrowToShipment = narrowToShipment;
		renderChargeTable();
	});

	$chargesWrap.find(".bco-select-all").on("click", function () {
		$tbody.find("tr.bco-charge-row:not(.bco-charge-row--disabled) .bco-charge-cb").prop("checked", true).trigger("change");
	});
}

function _bco_sync_parent_from_row(controls, parentValues, summary) {
	var map = {
		local_customer: summary.customer,
		customer: summary.customer,
		origin_port: summary.origin_port,
		destination_port: summary.destination_port,
		shipping_line: summary.shipping_line,
		airline: summary.airline,
		location_type: summary.location_type,
		location_from: summary.location_from,
		location_to: summary.location_to,
		customs_authority: summary.customs_authority,
		declaration_type: summary.declaration_type,
		customs_broker: summary.customs_broker,
	};
	controls.forEach(function (c) {
		var fn = c.spec.fieldname;
		var val = map[fn];
		if (val && !parentValues[fn]) {
			parentValues[fn] = val;
			if (c.read_only) {
				c.set_value(val);
			} else if (c.control) {
				c.control.set_value(val);
			}
		}
	});
}

function _bco_selected_includes_main_service(state, selectedNames) {
	var main = (state.preview.quote_meta && state.preview.quote_meta.main_service) || "";
	if (!String(main).trim()) {
		return true;
	}
	var byName = {};
	(state.preview.charge_rows || []).forEach(function (row) {
		byName[row.name] = row;
	});
	for (var i = 0; i < selectedNames.length; i++) {
		var row = byName[selectedNames[i]];
		if (row && row.matches_main_service) {
			return true;
		}
	}
	return false;
}

function _bco_execute_create(state, dialog, selected, payloadParent) {
	var preview = state.preview;
	var frm = state.frm;
	frappe.call({
		method: "logistics.utils.blanket_call_off.create_blanket_call_off",
		args: {
			sales_quote: frm.doc.name,
			target_doctype: preview.target_doctype,
			parent_fields: payloadParent,
			selected_charge_row_names: selected,
		},
		freeze: true,
		freeze_message: __("Creating…"),
		callback: function (r) {
			if (!r || r.exc || !r.message || !r.message.success) {
				frappe.msgprint(__("Call-off creation failed."));
				return;
			}
		dialog.hide();
		frappe.show_alert({
			message: r.message.message || __("Created."),
			indicator: "green",
		});
		var dt = r.message.doctype;
		var nm = r.message.name;
		if (dt && nm) {
			if (window.logistics_navigate_when_doc_exists) {
				window.logistics_navigate_when_doc_exists(dt, nm, function () {
					// Clear any cached document data before navigating to ensure fresh load
					if (frappe.model && frappe.model.clear_doc) {
						frappe.model.clear_doc(dt, nm);
					}
					frappe.set_route("Form", dt, nm);
				});
			} else {
				// Clear any cached document data before navigating to ensure fresh load
				if (frappe.model && frappe.model.clear_doc) {
					frappe.model.clear_doc(dt, nm);
				}
				frappe.set_route("Form", dt, nm);
			}
		}
		},
	});
}

function _bco_confirm_create(state, dialog) {
	var parentValues = state.parentValues;
	var preview = state.preview;
	var selected = [];
	dialog.$wrapper.find(".bco-charge-cb:checked").each(function () {
		var nm = $(this).closest(".bco-charge-row").attr("data-name");
		if (nm) selected.push(nm);
	});
	if (!selected.length) {
		frappe.msgprint(__("Select at least one charge line."));
		return;
	}

	var payloadParent = Object.assign({}, parentValues);
	delete payloadParent.service_type;
	delete payloadParent.target_doctype;

	var mainService =
		(preview.quote_meta && preview.quote_meta.main_service) ||
		(preview.quote_meta && preview.quote_meta.service_type_label) ||
		"";
	if (!_bco_selected_includes_main_service(state, selected) && String(mainService).trim()) {
		frappe.confirm(
			__(
				"The charges you selected do not include any line with the quote's main service type ({0}). Create the call-off anyway?",
				[mainService]
			),
			function () {
				_bco_execute_create(state, dialog, selected, payloadParent);
			}
		);
		return;
	}

	_bco_execute_create(state, dialog, selected, payloadParent);
}

logistics.view_blanket_call_offs = function (frm) {
	if (!frm || !frm.doc.name) return;
	var sq = frm.doc.name;
	var targets = [
		["Sea Booking", __("Sea Bookings")],
		["Air Booking", __("Air Bookings")],
		["Transport Order", __("Transport Orders")],
		["Declaration Order", __("Declaration Orders")],
	];
	var linkHtml = targets
		.map(function (t) {
			return (
				'<button type="button" class="btn btn-default btn-sm bco-view-link mb-2 mr-2" data-doctype="' +
				frappe.utils.escape_html(t[0]) +
				'">' +
				frappe.utils.escape_html(t[1]) +
				"</button>"
			);
		})
		.join("");
	var d = new frappe.ui.Dialog({
		title: __("View Call-Offs"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "links_html",
				options:
					'<p class="text-muted">' +
					__("Open linked documents created from Sales Quote {0}:", [sq]) +
					"</p><div class=\"bco-view-links\">" +
					linkHtml +
					"</div>",
			},
		],
		primary_action_label: __("Close"),
		primary_action: function () {
			d.hide();
		},
	});
	d.show();
	d.$wrapper.find(".bco-view-link").on("click", function () {
		var dt = $(this).attr("data-doctype");
		if (!dt) return;
		frappe.route_options = { sales_quote: sq };
		frappe.set_route("List", dt);
		d.hide();
	});
};
