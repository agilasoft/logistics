// Copyright (c) 2026, AgilaSoft and contributors
// Action → Initialize Tariff Schedule (Sales Quote)

frappe.provide("logistics");

var INIT_TARIFF_SCHEDULE_TITLE = __("Initialize Tariff Schedule");
var GCFTS_FILTER_GRID_SLOTS = 8;

function _gcfts_readonly_customer(frm) {
	if (!frm || !frm.doc) {
		return "";
	}
	return (frm.doc.customer_name || frm.doc.customer || "").trim();
}

function _gcfts_filter_specs(frm) {
	var specs = [
		{ key: "_svc", readonly: true, label: __("Main Service"), value: (frm.doc.main_service || "").trim() },
		{ key: "_cust", readonly: true, label: __("Customer"), value: _gcfts_readonly_customer(frm) },
	];
	var ms = (frm.doc.main_service || "").trim();
	var corridor = [
		{
			key: "origin_port",
			fieldtype: "Link",
			options: "UNLOCO",
			label: __("Origin Port"),
			value: frm.doc.origin_port || "",
		},
		{
			key: "destination_port",
			fieldtype: "Link",
			options: "UNLOCO",
			label: __("Destination Port"),
			value: frm.doc.destination_port || "",
		},
		{
			key: "load_type",
			fieldtype: "Link",
			options: "Load Type",
			label: __("Load Type"),
			value: frm.doc.load_type || "",
		},
		{
			key: "direction",
			fieldtype: "Select",
			options: "Import\nExport\nDomestic",
			label: __("Direction"),
			value: frm.doc.direction || "",
		},
		{
			key: "transport_mode",
			fieldtype: "Link",
			options: "Transport Mode",
			label: __("Transport Mode"),
			value: frm.doc.transport_mode || "",
		},
	];
	specs = specs.concat(corridor);
	if (ms === "Sea") {
		specs.push(
			{
				key: "shipping_line",
				fieldtype: "Link",
				options: "Shipping Line",
				label: __("Shipping Line"),
				value: frm.doc.shipping_line || "",
			},
			{
				key: "freight_agent_sea",
				fieldtype: "Link",
				options: "Freight Agent",
				label: __("Freight Agent (Sea)"),
				value: frm.doc.freight_agent_sea || "",
			}
		);
	} else if (ms === "Air") {
		specs.push({
			key: "airline",
			fieldtype: "Link",
			options: "Airline",
			label: __("Airline"),
			value: frm.doc.airline || "",
		},
		specs.push({
			key: "freight_agent",
			fieldtype: "Link",
			options: "Freight Agent",
			label: __("Freight Agent"),
			value: frm.doc.freight_agent || "",
		});
	} else if (ms === "Transport") {
		specs.push(
			{
				key: "location_from",
				fieldtype: "Data",
				label: __("Location From"),
				value: frm.doc.location_from || "",
			},
			{
				key: "location_to",
				fieldtype: "Data",
				label: __("Location To"),
				value: frm.doc.location_to || "",
			},
			{
				key: "vehicle_type",
				fieldtype: "Link",
				options: "Vehicle Type",
				label: __("Vehicle Type"),
				value: frm.doc.vehicle_type || "",
			}
		);
	} else if (ms === "Customs") {
		specs.push(
			{
				key: "customs_authority",
				fieldtype: "Link",
				options: "Customs Authority",
				label: __("Customs Authority"),
				value: frm.doc.customs_authority || "",
			},
			{
				key: "declaration_type",
				fieldtype: "Select",
				options: "Import\nExport\nTransit\nBonded",
				label: __("Declaration Type"),
				value: frm.doc.declaration_type || "",
			},
			{
				key: "customs_broker",
				fieldtype: "Link",
				options: "Customs Broker",
				label: __("Customs Broker"),
				value: frm.doc.customs_broker || "",
			}
		);
	}
	return specs;
}

function _gcfts_pad_specs(specs, n) {
	var out = specs.slice();
	while (out.length < n) {
		out.push({ placeholder: true, readonly: true, label: __("Filter field"), value: "", key: null });
	}
	return out.slice(0, n);
}

function _gcfts_mount_filter_cell($grid, spec, frm, dialog, idx) {
	var $cell = $('<div class="logistics-gcfq-filter-cell">').appendTo($grid);
	if (spec.placeholder) {
		$cell.append(
			$('<label class="logistics-gcfq-filter-label logistics-gcfq-filter-label--muted">').text(spec.label)
		);
		$cell.append(
			$('<input type="text" class="form-control input-sm logistics-gcfq-filter-input" readonly tabindex="-1">').attr(
				"placeholder",
				__("—")
			)
		);
		return;
	}
	$cell.append($('<label class="logistics-gcfq-filter-label">').text(spec.label));
	if (spec.readonly) {
		var $inp = $(
			'<input type="text" class="form-control input-sm logistics-gcfq-filter-input" readonly tabindex="-1">'
		).val(spec.value || "");
		$cell.append($inp);
		dialog._gcfts_filter_controls.push({
			key: spec.key,
			read_only: true,
			get_value: function () {
				return spec.value || "";
			},
		});
		return;
	}
	var df = {
		fieldname: "gcfts_filter_" + idx,
		label: "",
		fieldtype: spec.fieldtype,
		options: spec.options || "",
	};
	var ctrl = frappe.ui.form.make_control({ df: df, parent: $cell, render_input: true });
	ctrl.set_value(spec.value || "");
	dialog._gcfts_filter_controls.push({
		key: spec.key,
		read_only: false,
		get_value: function () {
			return ctrl.get_value();
		},
		control: ctrl,
	});
}

function _gcfts_filter_value_from_frm(frm, key) {
	if (!frm || !frm.doc || !key) {
		return "";
	}
	var v = frm.doc[key];
	return v == null ? "" : String(v).trim();
}

function _gcfts_capture_initial_filter_snapshot(dialog, frm) {
	dialog._gcfts_initial_filter_values = {};
	(dialog._gcfts_filter_controls || []).forEach(function (c) {
		if (!c.key || c.key.charAt(0) === "_") {
			return;
		}
		if (c.read_only) {
			return;
		}
		var v = frm && c.key ? _gcfts_filter_value_from_frm(frm, c.key) : c.get_value();
		dialog._gcfts_initial_filter_values[c.key] = v == null ? "" : String(v).trim();
	});
}

function _gcfts_collect_filter_overrides(dialog) {
	var o = {};
	var init = dialog._gcfts_initial_filter_values || {};
	(dialog._gcfts_filter_controls || []).forEach(function (c) {
		if (!c.key || c.key.charAt(0) === "_") {
			return;
		}
		if (c.read_only) {
			return;
		}
		var v = c.get_value();
		var s = v == null ? "" : String(v).trim();
		if (!Object.prototype.hasOwnProperty.call(init, c.key)) {
			o[c.key] = s;
			return;
		}
		var i = String(init[c.key] == null ? "" : init[c.key]).trim();
		if (s !== i) {
			o[c.key] = s;
		}
	});
	return o;
}

function _gcfts_mount_filter_panel($parent, frm, dialog, reloadList) {
	$parent.empty();
	dialog._gcfts_filter_controls = [];
	var $box = $('<div class="logistics-gcfq-filters">').appendTo($parent);
	$box.append($('<div class="logistics-gcfq-filters-title">').text(__("Scope filter criteria")));
	var $grid = $('<div class="logistics-gcfq-filters-grid">').appendTo($box);
	var specs = _gcfts_pad_specs(_gcfts_filter_specs(frm), GCFTS_FILTER_GRID_SLOTS);
	specs.forEach(function (spec, idx) {
		_gcfts_mount_filter_cell($grid, spec, frm, dialog, idx);
	});
	var timer;
	function schedule() {
		if (!dialog._gcfts_ready) {
			return;
		}
		if (timer) {
			clearTimeout(timer);
		}
		timer = setTimeout(function () {
			timer = null;
			reloadList();
		}, 350);
	}
	(dialog._gcfts_filter_controls || []).forEach(function (c) {
		if (c.read_only) {
			return;
		}
		if (c.control && c.control.$wrapper) {
			c.control.$wrapper.on("change", schedule);
		}
	});
	$("<button type='button' class='btn btn-sm btn-default'>")
		.text(__("Apply filters"))
		.appendTo($('<div class="gcfq-filter-actions">').appendTo($box))
		.on("click", reloadList);
}

logistics.should_show_initialize_tariff_schedule = function (frm) {
	if (!frm || !frm.doc || frm.doc.__islocal) {
		return false;
	}
	if (frm.doc.docstatus !== 0) {
		return false;
	}
	if (!(_gcfts_readonly_customer(frm) || "").trim()) {
		return false;
	}
	return frm.has_perm && frm.has_perm("write");
};

function _gcfts_format_preview_lines(charges) {
	if (!charges || !charges.length) {
		return __("No charge lines to show for this tariff.");
	}
	var lines = charges.slice(0, 12).map(function (ch) {
		var parts = [ch.item_code || ch.item_name || "—", ch.service_type || ""];
		if (ch.unit_rate != null) {
			parts.push(String(ch.unit_rate) + " " + (ch.currency || ""));
		}
		return parts.filter(Boolean).join(" · ");
	});
	var tail =
		charges.length > 12
			? "<p class='text-muted'>" + __("…and {0} more line(s).", [charges.length - 12]) + "</p>"
			: "";
	return lines.map(function (l) {
		return "<div>" + frappe.utils.escape_html(l) + "</div>";
	}).join("") + tail;
}

function _gcfts_load_card_preview($pv, frm, tariff_name, dialog, onDone) {
	$pv.html('<p class="text-muted">' + __("Loading preview…") + "</p>");
	frappe.call({
		method: "logistics.utils.get_tariff_schedule_for_sales_quote.preview_tariff_schedule_for_sales_quote",
		args: {
			docname: frm.doc.name,
			tariff_name: tariff_name,
			filter_overrides: _gcfts_collect_filter_overrides(dialog),
		},
		callback: function (r) {
			var msg = r.message || {};
			if (msg.error) {
				$pv.html('<div class="alert alert-warning">' + frappe.utils.escape_html(msg.error) + "</div>");
			} else {
				$pv.html(_gcfts_format_preview_lines(msg.charges || []));
			}
			if (onDone) {
				onDone(msg);
			}
		},
	});
}

function _gcfts_apply_tariff(frm, tariff_name, dialog) {
	frappe.confirm(
		__(
			"Apply Tariff {0}? Existing charge lines will be replaced with matching tariff schedule lines.",
			[tariff_name]
		),
		function () {
			frappe.call({
				method: "logistics.utils.get_tariff_schedule_for_sales_quote.apply_tariff_schedule_to_sales_quote",
				args: {
					docname: frm.doc.name,
					tariff_name: tariff_name,
					filter_overrides: _gcfts_collect_filter_overrides(dialog),
					replace_charges: 1,
				},
				freeze: true,
				freeze_message: __("Applying tariff schedule…"),
				callback: function (r) {
					if (r.message && r.message.success) {
						dialog.hide();
						frm.reload_doc();
						frappe.show_alert(
							{ message: r.message.message || __("Tariff applied."), indicator: "green" },
							5
						);
					}
				},
			});
		}
	);
}

function _gcfts_bind_cards($dynamic, frm, dialog) {
	$dynamic.find(".gcfq-card").each(function () {
		var $card = $(this);
		var tn = $card.attr("data-tariff-name") || "";
		var $pv = $card.find(".gcfq-card-preview");
		_gcfts_load_card_preview($pv, frm, tn, dialog);
		$card.find(".gcfq-card-apply").on("click", function () {
			_gcfts_apply_tariff(frm, tn, dialog);
		});
	});
}

function _gcfts_load_tariff_list(frm, dialog, $dynamic) {
	$dynamic.html('<p class="text-muted">' + __("Loading tariffs…") + "</p>");
	frappe.call({
		method: "logistics.utils.get_tariff_schedule_for_sales_quote.list_tariffs_for_sales_quote",
		args: {
			docname: frm.doc.name,
			filter_overrides: _gcfts_collect_filter_overrides(dialog),
		},
		callback: function (r) {
			if (r.exc) {
				$dynamic.html('<div class="alert alert-danger">' + __("Failed to load tariffs.") + "</div>");
				return;
			}
			var msg = r.message || {};
			var tariffs = msg.tariffs || [];
			if (!tariffs.length) {
				$dynamic.html(
					'<div class="alert alert-info">' +
						frappe.utils.escape_html(msg.message || __("No matching tariffs found.")) +
						"</div>"
				);
				return;
			}
			var $cards = $('<div class="gcfq-cards">');
			tariffs.forEach(function (row) {
				var tn = row.name;
				var title = row.tariff_name || tn;
				var $card = $('<div class="gcfq-card">').attr("data-tariff-name", tn);
				var $hd = $('<div class="gcfq-card-hd">');
				$hd.append($('<strong class="gcfq-card-title">').text(title));
				$hd.append(
					$('<button type="button" class="btn btn-xs btn-primary gcfq-card-apply">').text(__("Apply"))
				);
				var sub = [row.tariff_type || "", row.valid_from || "", row.valid_to || ""]
					.filter(Boolean)
					.join(" · ");
				if (sub) {
					$hd.append($('<div class="gcfq-card-sub text-muted">').text(sub));
				}
				var $bd = $('<div class="gcfq-card-bd">').append($('<div class="gcfq-card-preview">'));
				$card.append($hd).append($bd);
				$cards.append($card);
			});
			$dynamic.empty().append($('<div class="gcfq-cards-scroll">').append($cards));
			_gcfts_bind_cards($dynamic, frm, dialog);
		},
	});
}

logistics.open_initialize_tariff_schedule_dialog = function (frm) {
	if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
		frappe.msgprint(__("Save the Sales Quote first."));
		return;
	}
	if (!logistics.should_show_initialize_tariff_schedule(frm)) {
		frappe.msgprint(__("Initialize Tariff Schedule is not available for this document."));
		return;
	}
	var d = new frappe.ui.Dialog({
		title: INIT_TARIFF_SCHEDULE_TITLE,
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "tariff_area", options: '<div class="tariff-list"></div>' }],
		secondary_action_label: __("Close"),
		secondary_action: function () {
			d.hide();
		},
	});
	d.show();
	d.$wrapper.addClass("logistics-gcfq-dialog");
	var $wrap = d.$wrapper.find(".tariff-list").addClass("logistics-gcfq-quotation-list");
	var $filterMount = $('<div class="logistics-gcfq-filters-mount">').appendTo($wrap);
	var $dynamic = $('<div class="gcfq-dialog-dynamic">').appendTo($wrap);
	d._gcfts_ready = false;
	function reloadList() {
		_gcfts_load_tariff_list(frm, d, $dynamic);
	}
	_gcfts_mount_filter_panel($filterMount, frm, d, reloadList);
	setTimeout(function () {
		_gcfts_capture_initial_filter_snapshot(d, frm);
		d._gcfts_ready = true;
		reloadList();
	}, 0);
};

logistics.add_initialize_tariff_schedule_button = function (frm) {
	if (
		typeof logistics.should_show_initialize_tariff_schedule !== "function" ||
		!logistics.should_show_initialize_tariff_schedule(frm)
	) {
		return;
	}
	frm.add_custom_button(INIT_TARIFF_SCHEDULE_TITLE, function () {
		if (logistics.open_initialize_tariff_schedule_dialog) {
			logistics.open_initialize_tariff_schedule_dialog(frm);
		}
	}, __("Action"));
};
