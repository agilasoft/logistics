// Copyright (c) 2026, AgilaSoft and contributors
// Shared: Action → Get Charges from Quotation (Sea Booking, Air Booking, Transport Order, Declaration Order)

frappe.provide("logistics");

var GET_CHARGES_TITLE_LIST = __("Get Charges from Quotation");
var GCFQ_FILTER_GRID_SLOTS = 12;

var DECLARATION_TYPE_OPTIONS = "Import\nExport\nTransit\nBonded";

/**
 * Per–job-type filter fields (editable). Keys must match server GCFQ_FILTER_KEYS.
 * @param {frappe.ui.form.Form} frm
 */
function _gcfq_filter_specs(frm) {
	var d = frm.doctype;
	if (d === "Sea Booking") {
		return [
			{
				key: "_svc",
				readonly: true,
				label: __("Service type"),
				value: __("Sea"),
			},
			{
				key: "_cust",
				readonly: true,
				label: __("Local Customer"),
				value: frm.doc.local_customer || "",
			},
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
				key: "shipping_line",
				fieldtype: "Link",
				options: "Shipping Line",
				label: __("Shipping Line"),
				value: frm.doc.shipping_line || "",
			},
			{
				key: "branch",
				fieldtype: "Link",
				options: "Branch",
				label: __("Branch"),
				value: frm.doc.branch || "",
			},
			{
				key: "cost_center",
				fieldtype: "Link",
				options: "Cost Center",
				label: __("Cost Center"),
				value: frm.doc.cost_center || "",
			},
			{
				key: "profit_center",
				fieldtype: "Link",
				options: "Profit Center",
				label: __("Profit Center"),
				value: frm.doc.profit_center || "",
			},
		];
	}
	if (d === "Air Booking") {
		return [
			{
				key: "_svc",
				readonly: true,
				label: __("Service type"),
				value: __("Air"),
			},
			{
				key: "_cust",
				readonly: true,
				label: __("Local Customer"),
				value: frm.doc.local_customer || "",
			},
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
				key: "airline",
				fieldtype: "Link",
				options: "Airline",
				label: __("Airline"),
				value: frm.doc.airline || "",
			},
			{
				key: "branch",
				fieldtype: "Link",
				options: "Branch",
				label: __("Branch"),
				value: frm.doc.branch || "",
			},
			{
				key: "cost_center",
				fieldtype: "Link",
				options: "Cost Center",
				label: __("Cost Center"),
				value: frm.doc.cost_center || "",
			},
			{
				key: "profit_center",
				fieldtype: "Link",
				options: "Profit Center",
				label: __("Profit Center"),
				value: frm.doc.profit_center || "",
			},
		];
	}
	if (d === "Transport Order") {
		var locSpecs = [
			{
				key: "_svc",
				readonly: true,
				label: __("Service type"),
				value: __("Transport"),
			},
			{
				key: "_cust",
				readonly: true,
				label: __("Customer"),
				value: frm.doc.customer || "",
			},
		];
		if (frm.doc.location_type) {
			locSpecs.push(
				{
					key: "location_from",
					fieldtype: "Dynamic Link",
					options: "location_type",
					label: __("Location From"),
					value: frm.doc.location_from || "",
					get_options: function () {
						return frm.doc.location_type || "";
					},
				},
				{
					key: "location_to",
					fieldtype: "Dynamic Link",
					options: "location_type",
					label: __("Location To"),
					value: frm.doc.location_to || "",
					get_options: function () {
						return frm.doc.location_type || "";
					},
				}
			);
		} else {
			locSpecs.push(
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
				}
			);
		}
		locSpecs.push(
			{
				key: "branch",
				fieldtype: "Link",
				options: "Branch",
				label: __("Branch"),
				value: frm.doc.branch || "",
			},
			{
				key: "cost_center",
				fieldtype: "Link",
				options: "Cost Center",
				label: __("Cost Center"),
				value: frm.doc.cost_center || "",
			},
			{
				key: "profit_center",
				fieldtype: "Link",
				options: "Profit Center",
				label: __("Profit Center"),
				value: frm.doc.profit_center || "",
			}
		);
		return locSpecs;
	}
	if (d === "Declaration Order") {
		return [
			{
				key: "_svc",
				readonly: true,
				label: __("Service type"),
				value: __("Customs"),
			},
			{
				key: "_cust",
				readonly: true,
				label: __("Customer"),
				value: frm.doc.customer || "",
			},
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
				select_options: DECLARATION_TYPE_OPTIONS,
				label: __("Declaration Type"),
				value: frm.doc.declaration_type || "",
			},
			{
				key: "customs_broker",
				fieldtype: "Link",
				options: "Broker",
				label: __("Customs Broker"),
				value: frm.doc.customs_broker || "",
			},
			{
				key: "transport_mode",
				fieldtype: "Link",
				options: "Transport Mode",
				label: __("Transport Mode"),
				value: frm.doc.transport_mode || "",
			},
			{
				key: "port_of_loading",
				fieldtype: "Link",
				options: "UNLOCO",
				label: __("Port of Loading/Entry"),
				value: frm.doc.port_of_loading || "",
			},
			{
				key: "port_of_discharge",
				fieldtype: "Link",
				options: "UNLOCO",
				label: __("Port of Discharge/Exit"),
				value: frm.doc.port_of_discharge || "",
			},
			{
				key: "branch",
				fieldtype: "Link",
				options: "Branch",
				label: __("Branch"),
				value: frm.doc.branch || "",
			},
			{
				key: "cost_center",
				fieldtype: "Link",
				options: "Cost Center",
				label: __("Cost Center"),
				value: frm.doc.cost_center || "",
			},
			{
				key: "profit_center",
				fieldtype: "Link",
				options: "Profit Center",
				label: __("Profit Center"),
				value: frm.doc.profit_center || "",
			},
		];
	}
	return [];
}

function _gcfq_pad_specs(specs, n) {
	var out = specs.slice();
	while (out.length < n) {
		out.push({
			placeholder: true,
			readonly: true,
			label: __("Filter field"),
			value: "",
			key: null,
		});
	}
	return out.slice(0, n);
}

function _gcfq_mount_filter_cell($grid, spec, frm, dialog, idx) {
	var $cell = $('<div class="logistics-gcfq-filter-cell">').appendTo($grid);
	if (spec.placeholder) {
		$cell.append(
			$('<label class="logistics-gcfq-filter-label logistics-gcfq-filter-label--muted">').text(
				spec.label
			)
		);
		$cell.append(
			$(
				'<input type="text" class="form-control input-sm logistics-gcfq-filter-input" readonly tabindex="-1">'
			).attr("placeholder", __("—"))
		);
		return;
	}
	$cell.append($('<label class="logistics-gcfq-filter-label">').text(spec.label));
	if (spec.readonly) {
		var $inp = $(
			'<input type="text" class="form-control input-sm logistics-gcfq-filter-input" readonly tabindex="-1">'
		).val(spec.value || "");
		$cell.append($inp);
		dialog._gcfq_filter_controls.push({
			key: spec.key,
			read_only: true,
			get_value: function () {
				return spec.value || "";
			},
		});
		return;
	}
	var df = {
		fieldname: "gcfq_filter_" + idx,
		label: "",
		fieldtype: spec.fieldtype,
		options: spec.options || "",
	};
	if (spec.fieldtype === "Select" && spec.select_options) {
		df.options = spec.select_options;
	}
	if (spec.fieldtype === "Dynamic Link" && spec.get_options) {
		df.get_options = spec.get_options;
	}
	var ctrl = frappe.ui.form.make_control({
		df: df,
		parent: $cell,
		render_input: true,
	});
	ctrl.set_value(spec.value || "");
	dialog._gcfq_filter_controls.push({
		key: spec.key,
		read_only: false,
		get_value: function () {
			return ctrl.get_value();
		},
		control: ctrl,
	});
}

function _gcfq_capture_initial_filter_snapshot(dialog) {
	dialog._gcfq_initial_filter_values = {};
	(dialog._gcfq_filter_controls || []).forEach(function (c) {
		if (!c.key || c.key.charAt(0) === "_") {
			return;
		}
		if (c.read_only) {
			return;
		}
		var v = c.get_value();
		dialog._gcfq_initial_filter_values[c.key] = v == null ? "" : String(v).trim();
	});
}

/**
 * Only send keys the user changed vs. dialog open. Omitting a key lets the server use the saved document
 * (avoids empty Link controls overwriting booking airline / ports).
 */
function _gcfq_collect_filter_overrides(dialog) {
	var o = {};
	var init = dialog._gcfq_initial_filter_values || {};
	(dialog._gcfq_filter_controls || []).forEach(function (c) {
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
		if (s === i) {
			return;
		}
		o[c.key] = s;
	});
	return o;
}

function _gcfq_bind_filter_change_reload(dialog, reloadList) {
	var timer;
	function schedule() {
		if (timer) {
			clearTimeout(timer);
		}
		timer = setTimeout(function () {
			timer = null;
			reloadList();
		}, 350);
	}
	(dialog._gcfq_filter_controls || []).forEach(function (c) {
		if (c.read_only) {
			return;
		}
		if (c.control && c.control.$wrapper) {
			c.control.$wrapper.on("change", schedule);
		}
	});
}

function _gcfq_mount_filter_panel($parent, frm, dialog, reloadList) {
	$parent.empty();
	dialog._gcfq_filter_controls = [];
	var $box = $('<div class="logistics-gcfq-filters">').appendTo($parent);
	$box.append(
		$('<div class="logistics-gcfq-filters-title">').text(__("List filter criteria"))
	);
	var $grid = $('<div class="logistics-gcfq-filters-grid">').appendTo($box);
	var specs = _gcfq_pad_specs(_gcfq_filter_specs(frm), GCFQ_FILTER_GRID_SLOTS);
	specs.forEach(function (spec, idx) {
		_gcfq_mount_filter_cell($grid, spec, frm, dialog, idx);
	});
	_gcfq_bind_filter_change_reload(dialog, reloadList);
	var $actions = $('<div class="gcfq-filter-actions">').appendTo($box);
	$("<button type='button' class='btn btn-sm btn-default'>")
		.text(__("Apply filters"))
		.appendTo($actions)
		.on("click", function () {
			reloadList();
		});
}

/**
 * Open dialog: filter grid → expandable cards per Sales Quote (charge preview) → Apply.
 * @param {frappe.ui.form.Form} frm
 */
logistics.open_get_charges_from_quotation_dialog = function (frm) {
	if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
		frappe.msgprint(__("Save the document first."));
		return;
	}
	if (frm.doc.docstatus !== 0) {
		frappe.msgprint(__("Only draft documents can load charges from a quotation."));
		return;
	}

	var cust =
		frm.doctype === "Transport Order" || frm.doctype === "Declaration Order"
			? frm.doc.customer
			: frm.doc.local_customer;
	if (!cust) {
		frappe.msgprint(
			__(
				frm.doctype === "Transport Order" || frm.doctype === "Declaration Order"
					? "Set Customer first."
					: "Set Local Customer first."
			)
		);
		return;
	}

	var d = new frappe.ui.Dialog({
		title: GET_CHARGES_TITLE_LIST,
		size: "large",
		no_focus: true,
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "quotes_area",
				options: '<div class="quotation-list"></div>',
			},
		],
		secondary_action_label: __("Close"),
		secondary_action: function () {
			d.hide();
		},
	});

	d.onhide = function () {
		(d._gcfq_filter_controls || []).forEach(function (c) {
			if (c.control && c.control.$wrapper) {
				c.control.$wrapper.remove();
			}
		});
		d._gcfq_filter_controls = [];
	};

	d.show();
	d.$wrapper.addClass("logistics-gcfq-dialog");

	var $wrap = d.$wrapper.find(".quotation-list");
	$wrap.addClass("logistics-gcfq-quotation-list");
	$wrap.empty();
	var $filterMount = $('<div class="logistics-gcfq-filters-mount">').appendTo($wrap);
	var $dynamic = $('<div class="gcfq-dialog-dynamic">').appendTo($wrap);

	function reloadList() {
		_load_quote_list(frm, d, $dynamic);
	}

	_gcfq_mount_filter_panel($filterMount, frm, d, reloadList);
	// Defer snapshot + first load so Link/Select controls finish populating (avoids sending "" overrides).
	setTimeout(function () {
		_gcfq_capture_initial_filter_snapshot(d);
		reloadList();
	}, 0);
};

function _set_dialog_title(dialog, title) {
	if (dialog && dialog.set_title) {
		dialog.set_title(title);
	}
}

/** @param {Record<string, unknown>|null|undefined} filters */
function _gcfq_filters_rules_html(filters) {
	if (!filters || typeof filters !== "object") {
		return "";
	}
	var rules = filters.rules;
	if (!Array.isArray(rules) || !rules.length) {
		return "";
	}
	var parts = [
		'<div class="logistics-gcfq-filters-rules-block">',
		'<div class="logistics-gcfq-filters-rules-title">' + __("Also required") + "</div>",
		'<ul class="logistics-gcfq-filters-rules">',
	];
	rules.forEach(function (rule) {
		parts.push("<li>" + frappe.utils.escape_html(String(rule)) + "</li>");
	});
	parts.push("</ul></div>");
	return parts.join("");
}

function _gcfq_quote_icon_letter(name) {
	var s = String(name || "");
	var m = s.match(/[A-Za-z0-9]/);
	return m ? m[0].toUpperCase() : "?";
}

/**
 * @param {Record<string, unknown>} m preview_quotation_charges_for_job message
 * @returns {string} inner HTML (toolbar + table or empty / error — caller wraps)
 */
function _gcfq_preview_charges_inner_html(m) {
	if (!m || typeof m !== "object") {
		return (
			'<div class="logistics-gcfq-preview-empty">' + __("Preview failed.") + "</div>"
		);
	}
	if (m.error) {
		return (
			'<div class="alert alert-danger mb-0">' +
			frappe.utils.escape_html(String(m.error)) +
			"</div>"
		);
	}
	var charges = Array.isArray(m.charges) ? m.charges : [];
	var cnt = m.charges_count != null ? m.charges_count : charges.length;
	var lines =
		'<div class="logistics-gcfq-preview logistics-gcfq-preview--in-card">' +
		'<div class="logistics-gcfq-preview-toolbar">' +
		'<span class="logistics-gcfq-preview-toolbar-title">' +
		__("Charge preview") +
		"</span>" +
		'<span class="logistics-gcfq-preview-count">' +
		frappe.utils.escape_html(String(cnt)) +
		" " +
		__(cnt === 1 ? "charge line" : "charge lines") +
		"</span></div>";

	if (!charges.length) {
		lines +=
			'<div class="logistics-gcfq-preview-empty">' +
			__("No charge lines to show for this quotation.") +
			"</div></div>";
		return lines;
	}

	lines +=
		'<div class="logistics-gcfq-table-wrap logistics-gcfq-preview-table-wrap">' +
		'<table class="logistics-gcfq-table logistics-gcfq-preview-table">' +
		"<thead><tr>" +
		"<th>" +
		__("Service type") +
		"</th><th>" +
		__("Item code") +
		"</th><th>" +
		__("Item name") +
		"</th><th class='gcfq-preview-th-rate'>" +
		__("Unit rate") +
		"</th></tr></thead><tbody>";
	charges.slice(0, 40).forEach(function (c) {
		if (!c || typeof c !== "object") {
			return;
		}
		var ic = c.item_code || c.charge_item || "";
		var nm = c.item_name || c.charge_name || "";
		var st = (c.service_type && String(c.service_type).trim()) || "";
		var stCell =
			st !== ""
				? '<span class="gcfq-preview-service-pill">' +
				  frappe.utils.escape_html(st) +
				  "</span>"
				: '<span class="gcfq-preview-empty-cell">—</span>';
		lines +=
			"<tr>" +
			"<td class='gcfq-preview-col-service'>" +
			stCell +
			"</td><td class='gcfq-preview-col-code'>" +
			frappe.utils.escape_html(ic != null ? String(ic) : "") +
			"</td><td class='gcfq-preview-col-name'>" +
			frappe.utils.escape_html(nm != null ? String(nm) : "") +
			"</td><td class='gcfq-preview-col-rate'>" +
			_gcfq_unit_rate_display(c) +
			"</td></tr>";
	});
	lines += "</tbody></table></div>";
	if (charges.length > 40) {
		lines +=
			'<p class="logistics-gcfq-preview-more text-muted mb-0">' +
			__("Showing first 40 lines.") +
			" " +
			__("More lines will still be applied.") +
			"</p>";
	}
	lines += "</div>";
	return lines;
}

function _gcfq_card_loading_html() {
	return (
		'<div class="gcfq-card-loading">' +
		'<span class="gcfq-card-loading-spin"></span>' +
		'<span>' +
		__("Loading charge preview…") +
		"</span></div>"
	);
}

function _gcfq_load_card_preview($pv, frm, sales_quote, dialog, onDone) {
	$pv.removeData("gcfq-charges-count");
	$pv.html(_gcfq_card_loading_html());
	var fo = _gcfq_collect_filter_overrides(dialog);
	frappe.call({
		method: "logistics.utils.get_charges_from_quotation.preview_quotation_charges_for_job",
		args: {
			doctype: frm.doctype,
			docname: frm.doc.name,
			sales_quote: sales_quote,
			filter_overrides: fo,
		},
		callback: function (r) {
			if (!r || r.exc) {
				$pv.html(
					'<div class="alert alert-danger mb-0">' + __("Preview failed.") + "</div>"
				);
				if (onDone) {
					onDone(0);
				}
				return;
			}
			var m = r.message || {};
			$pv.html(_gcfq_preview_charges_inner_html(m));
			var cnt = 0;
			if (!m.error) {
				var charges = Array.isArray(m.charges) ? m.charges : [];
				cnt = m.charges_count != null ? m.charges_count : charges.length;
			}
			$pv.data("gcfq-charges-count", cnt);
			if (onDone) {
				onDone(cnt);
			}
		},
		error: function () {
			$pv.html(
				'<div class="alert alert-danger mb-0">' +
					__(
						"Could not load the preview. Check your connection or try again. If the problem continues, ask an administrator to check the server error log."
					) +
					"</div>"
			);
			if (onDone) {
				onDone(0);
			}
		},
	});
}

function _gcfq_apply_quotation(frm, sales_quote, dialog) {
	frappe.confirm(
		__(
			"Apply charges and link Sales Quote {0}? Existing charge lines will be replaced.",
			[sales_quote]
		),
		function () {
			var fo = _gcfq_collect_filter_overrides(dialog);
			frappe.call({
				method: "logistics.utils.get_charges_from_quotation.apply_quotation_charges_to_job",
				args: {
					doctype: frm.doctype,
					docname: frm.doc.name,
					sales_quote: sales_quote,
					filter_overrides: fo,
				},
				freeze: true,
				freeze_message: __("Applying…"),
				callback: function (r2) {
					if (!r2 || r2.exc) {
						frappe.msgprint(__("Apply failed."));
						return;
					}
					dialog.hide();
					frappe.show_alert({
						message: (r2.message && r2.message.message) || __("Applied."),
						indicator: "green",
					});
					frm.reload_doc();
				},
			});
		}
	);
}

function _gcfq_bind_quote_search($root) {
	$root.off(".gcfqSearch");
	$root.on("input.gcfqSearch", ".gcfq-quote-search", function () {
		_gcfq_run_quote_search($root);
	});
}

function _gcfq_run_quote_search($root) {
	var q = String($root.find(".gcfq-quote-search").val() || "")
		.toLowerCase()
		.trim();
	var $cards = $root.find(".gcfq-card");
	var visible = 0;
	$cards.each(function () {
		var hay = ($(this).attr("data-gcfq-search") || "").toLowerCase();
		var show = !q || hay.indexOf(q) !== -1;
		$(this).toggle(show);
		if (show) {
			visible++;
		}
	});
	$root.find(".gcfq-quote-search-empty").toggle(q.length > 0 && visible === 0);
}

function _gcfq_bind_quote_cards($wrap, frm, dialog) {
	$wrap.off(".gcfq");
	$wrap.on("click.gcfq", ".gcfq-card-toggle", function () {
		var $card = $(this).closest(".gcfq-card");
		$card.toggleClass("open");
		if (!$card.hasClass("open")) {
			return;
		}
		var $pv = $card.find(".gcfq-card-preview");
		if ($pv.data("gcfq-loaded")) {
			return;
		}
		var sq = $card.attr("data-sales-quote") || "";
		var $btn = $card.find(".gcfq-card-apply");
		_gcfq_load_card_preview($pv, frm, sq, dialog, function (cnt) {
			$pv.data("gcfq-loaded", true);
			$btn.prop("disabled", !cnt);
		});
	});
	$wrap.on("keydown.gcfq", ".gcfq-card-toggle", function (e) {
		if (e.which === 13 || e.which === 32) {
			e.preventDefault();
			$(this).trigger("click");
		}
	});
	$wrap.on("click.gcfq", ".gcfq-card-apply", function (e) {
		e.preventDefault();
		e.stopPropagation();
		var $card = $(this).closest(".gcfq-card");
		var sq = $card.attr("data-sales-quote") || "";
		var $pv = $card.find(".gcfq-card-preview");
		if (!$pv.data("gcfq-loaded")) {
			$card.addClass("open");
			var $btn = $(this);
			_gcfq_load_card_preview($pv, frm, sq, dialog, function (cnt) {
				$pv.data("gcfq-loaded", true);
				$btn.prop("disabled", !cnt);
				if (cnt) {
					_gcfq_apply_quotation(frm, sq, dialog);
				}
			});
			return;
		}
		var cnt = $pv.data("gcfq-charges-count");
		if (cnt === undefined || cnt === 0) {
			frappe.msgprint({
				message: __("Expand the card to load charges, or there are no charge lines to apply."),
				indicator: "orange",
			});
			return;
		}
		_gcfq_apply_quotation(frm, sq, dialog);
	});
}

function _load_quote_list(frm, dialog, $dynamic) {
	_set_dialog_title(dialog, GET_CHARGES_TITLE_LIST);
	var filter_overrides = _gcfq_collect_filter_overrides(dialog);

	$dynamic.html('<p class="text-muted">' + __("Loading quotations…") + "</p>");

	frappe.call({
		method: "logistics.utils.get_charges_from_quotation.list_sales_quotes_for_job",
		args: {
			doctype: frm.doctype,
			docname: frm.doc.name,
			filter_overrides: filter_overrides,
		},
		callback: function (r) {
			if (!r || r.exc) {
				$dynamic.html(
					'<div class="alert alert-danger">' + __("Failed to load quotations.") + "</div>"
				);
				return;
			}
			var msg = (r.message && r.message.message) || "";
			var quotes = (r.message && r.message.quotes) || [];
			var filters = r.message && r.message.filters;
			var rulesHtml = _gcfq_filters_rules_html(filters);

			if (!quotes.length) {
				$dynamic.html(
					'<div class="alert alert-warning logistics-gcfq-status-alert mb-0">' +
						frappe.utils.escape_html(msg || __("No matching Sales Quotes found.")) +
						"</div>" +
						rulesHtml
				);
				return;
			}

			var $root = $('<div class="logistics-gcfq-list-root">');

			var $searchWrap = $('<div class="gcfq-quote-search-wrap">');
			var $searchInput = $("<input>")
				.attr("type", "search")
				.addClass("form-control input-sm gcfq-quote-search")
				.attr("autocomplete", "off")
				.attr(
					"placeholder",
					__("Search by quotation, customer, corridor…")
				);
			$searchWrap.append($searchInput);
			$root.append($searchWrap);

			var $scroll = $('<div class="gcfq-cards-scroll">');
			var $cards = $('<div class="gcfq-cards">');
			quotes.forEach(function (row) {
				var o =
					frm.doctype === "Transport Order"
						? row.location_from || ""
						: row.origin_port || "";
				var dest =
					frm.doctype === "Transport Order"
						? row.location_to || ""
						: row.destination_port || "";
				var sq = row.name || "";
				var searchBlob = [
					sq,
					row.customer || "",
					String(o || ""),
					String(dest || ""),
					row.status || "",
					row.company || "",
					row.valid_until || "",
				]
					.join(" ")
					.toLowerCase();
				var $card = $('<div class="gcfq-card">')
					.attr("data-sales-quote", sq)
					.attr("data-gcfq-search", searchBlob);
				var $hd = $('<div class="gcfq-card-hd">');
				var $toggle = $('<div class="gcfq-card-toggle" role="button" tabindex="0">');
				$toggle.append($('<span class="gcfq-card-chevron">').text("\u25B8"));
				var $block = $('<div class="gcfq-card-head-block">');
				var iconLetter = _gcfq_quote_icon_letter(sq);
				var $icon = $('<span class="gcfq-card-mono-icon">').text(iconLetter);
				$block.append($icon);
				var $text = $('<div class="gcfq-card-head-text">');
				$text.append($('<div class="gcfq-card-head-title">').text(sq));
				var $row2 = $('<div class="gcfq-card-head-row2">');
				$row2.append(
					$('<span class="gcfq-card-pill">').text(
						String(o || "") + " → " + String(dest || "")
					)
				);
				var subParts = [row.status || "", row.date || ""].filter(function (x) {
					return String(x || "").trim() !== "";
				});
				if (subParts.length) {
					$row2.append($('<span class="gcfq-card-sub">').text(subParts.join(" · ")));
				}
				$text.append($row2);
				$block.append($text);
				$toggle.append($block);
				var $apply = $("<button type='button'>")
					.addClass("btn btn-primary btn-sm gcfq-card-apply")
					.prop("disabled", true)
					.attr("title", __("Apply charges from this quotation"))
					.text(__("Apply"));
				$hd.append($toggle).append($apply);
				var $bd = $('<div class="gcfq-card-bd">');
				var $pv = $('<div class="gcfq-card-preview">');
				$bd.append($pv);
				$card.append($hd).append($bd);
				$cards.append($card);
			});
			var $searchEmpty = $("<p>")
				.addClass("gcfq-quote-search-empty text-muted")
				.text(__("No quotations match your search."))
				.hide();
			$scroll.append($cards).append($searchEmpty);
			$root.append($scroll);
			if (rulesHtml) {
				$root.append(rulesHtml);
			}

			$dynamic.empty().append($root);
			_gcfq_bind_quote_cards($dynamic, frm, dialog);
			_gcfq_bind_quote_search($root);
		},
	});
}

/** @returns {string} HTML cell content for unit rate (uses rate, then unit_rate; currency when set). */
function _gcfq_unit_rate_display(c) {
	var raw =
		c.rate !== undefined && c.rate !== null && c.rate !== ""
			? c.rate
			: c.unit_rate !== undefined && c.unit_rate !== null && c.unit_rate !== ""
				? c.unit_rate
				: null;
	if (raw === null || raw === undefined || raw === "") {
		return '<span class="gcfq-preview-empty-cell">—</span>';
	}
	var num =
		typeof flt === "function"
			? flt(raw, 9)
			: parseFloat(String(raw).replace(/,/g, "")) || 0;
	var cur = (c.currency || c.selling_currency || "").trim();
	var text;
	if (cur && typeof format_currency === "function") {
		try {
			text = format_currency(num, cur);
		} catch (e) {
			text = format_number(num, null, 2);
		}
	} else if (typeof format_number === "function") {
		text = format_number(num, null, 2);
	} else {
		text = String(Math.round(num * 100) / 100);
	}
	return frappe.utils.escape_html(text);
}

/**
 * Header quantity snapshot for calculate_charge_row while the parent form has unsaved packing/routing changes.
 * Server loads parent via get_doc (DB); merging this keeps revenue/cost quantities aligned with the desk.
 * @param {frappe.ui.form.Form} frm
 * @returns {string|null} JSON string or null
 */
logistics.charge_row_parent_overrides = function (frm) {
	if (!frm || !frm.doc) {
		return null;
	}
	var d = frm.doc;
	var dt = frm.doctype;
	var keys = [];
	if (dt === "Air Booking" || dt === "Air Shipment") {
		keys = [
			"total_weight",
			"weight",
			"chargeable_weight",
			"chargeable",
			"total_volume",
			"volume",
			"total_pieces",
			"total_packages",
			"pieces",
		];
	} else if (dt === "Sea Booking" || dt === "Sea Shipment") {
		keys = [
			"total_weight",
			"weight",
			"total_volume",
			"volume",
			"total_pieces",
			"total_packages",
			"total_teu",
			"teu",
			"total_containers",
			"pieces",
		];
	} else if (dt === "Sea Consolidation") {
		keys = [
			"total_weight",
			"weight",
			"chargeable_weight",
			"chargeable",
			"total_volume",
			"volume",
			"total_packages",
			"total_pieces",
			"total_teu",
			"teu",
			"total_containers",
			"pieces",
		];
	} else if (dt === "Transport Order" || dt === "Transport Job") {
		keys = [
			"total_weight",
			"weight",
			"total_volume",
			"volume",
			"total_distance",
			"distance",
			"total_pieces",
			"total_packages",
			"pieces",
		];
	} else if (dt === "Declaration" || dt === "Declaration Order") {
		keys = [
			"total_weight",
			"weight",
			"total_volume",
			"volume",
			"total_pieces",
			"total_packages",
			"pieces",
		];
	} else if (dt === "Warehouse Job") {
		keys = [
			"total_weight",
			"weight",
			"total_volume",
			"volume",
			"total_pieces",
			"total_packages",
			"pieces",
		];
	} else {
		return null;
	}
	var o = {};
	keys.forEach(function (k) {
		var v = d[k];
		if (v !== undefined && v !== null && v !== "") {
			o[k] = v;
		}
	});
	return Object.keys(o).length ? JSON.stringify(o) : null;
};

/**
 * Mirror logistics.utils.charges_calculation._get_quantity_for_calculation_method (Per Unit)
 * for Air Booking / Air Shipment headers so quantity updates when unit_type changes on the desk.
 * @param {object} d Parent doc (frm.doc)
 * @param {string|null|undefined} unit_type
 * @returns {number}
 */
logistics.resolve_air_parent_quantity_by_unit_type = function (d, unit_type) {
	if (!d || !unit_type || !String(unit_type).trim()) {
		return 1;
	}
	var ut = String(unit_type).trim().toLowerCase();
	var flt = frappe.utils.flt;

	function pick_weight() {
		var order = ["total_weight", "chargeable_weight", "weight", "chargeable", "air_weight"];
		for (var i = 0; i < order.length; i++) {
			var k = order[i];
			if (d[k] !== undefined && d[k] !== null && d[k] !== "") {
				return flt(d[k]);
			}
		}
		return 0;
	}
	function pick_chargeable() {
		var order = ["chargeable", "chargeable_weight"];
		for (var i = 0; i < order.length; i++) {
			var k = order[i];
			if (d[k] !== undefined && d[k] !== null && d[k] !== "") {
				return flt(d[k]);
			}
		}
		return 0;
	}
	function pick_volume() {
		var order = ["total_volume", "volume", "air_volume"];
		for (var i = 0; i < order.length; i++) {
			var k = order[i];
			if (d[k] !== undefined && d[k] !== null && d[k] !== "") {
				return flt(d[k]);
			}
		}
		return 0;
	}
	function pick_pieces() {
		var p = flt(d.total_pieces);
		if (p) {
			return p;
		}
		p = flt(d.total_packages);
		if (p) {
			return p;
		}
		p = flt(d.pieces);
		if (p) {
			return p;
		}
		if (d.packages && d.packages.length) {
			return flt(d.packages.length);
		}
		return 0;
	}

	if (ut === "weight") {
		return pick_weight();
	}
	if (ut === "chargeable weight") {
		var cw = pick_chargeable();
		if (cw > 0) {
			return cw;
		}
		return pick_weight();
	}
	if (ut === "volume") {
		return pick_volume();
	}
	if (ut === "package" || ut === "piece") {
		return pick_pieces();
	}
	if (ut === "distance") {
		return flt(d.total_distance || d.distance || 0);
	}
	if (ut === "teu") {
		return flt(d.total_teu || d.teu || 0);
	}
	if (ut === "container") {
		return flt(d.total_containers || 0);
	}
	if (ut === "operation time") {
		var ot = flt(d.total_operation_time || d.operation_time || d.actual_hours || 0);
		return ot > 0 ? ot : 1;
	}
	if (ut === "job" || ut === "shipment") {
		return 1;
	}
	if (ut === "trip") {
		var legs = d.legs || d.routing_legs || [];
		var t = legs.length ? flt(legs.length) : 0;
		return t > 0 ? t : 1;
	}
	var fallback = pick_weight() || pick_volume() || pick_pieces();
	return fallback > 0 ? fallback : 1;
};

/**
 * Repaint one child-table cell in the parent form grid (list view updates immediately).
 * @param {frappe.ui.form.Form} frm
 * @param {string} cdt Child doctype
 * @param {string} cdn Child row name
 * @param {string} fieldname
 */
logistics.refresh_charge_grid_cell = function (frm, cdt, cdn, fieldname) {
	if (!frm || !frm.fields_dict || !cdt || !cdn || !fieldname) {
		return;
	}
	var parentfield = null;
	(frappe.meta.get_docfields(frm.doctype) || []).forEach(function (df) {
		if (df.fieldtype === "Table" && df.options === cdt) {
			parentfield = df.fieldname;
		}
	});
	if (!parentfield) {
		return;
	}
	var grid = frm.fields_dict[parentfield] && frm.fields_dict[parentfield].grid;
	if (!grid) {
		return;
	}
	var grid_row = grid.grid_rows_by_docname && grid.grid_rows_by_docname[cdn];
	if (!grid_row && grid.grid_rows && grid.grid_rows.length) {
		for (var i = 0; i < grid.grid_rows.length; i++) {
			var gr = grid.grid_rows[i];
			if (gr.doc && gr.doc.name === cdn) {
				grid_row = gr;
				break;
			}
		}
	}
	if (grid_row && grid_row.refresh_field) {
		grid_row.refresh_field(fieldname);
		return;
	}
	if (frm.refresh_field) {
		frm.refresh_field(parentfield);
	}
};

/**
 * When unit_type / cost_unit_type changes: write quantity to the model and refresh the grid cell
 * immediately (mutating locals alone does not update the charge grid until save).
 * Uses row._logistics_skip_charge_recalc so the quantity/cost_quantity triggers do not re-RPC.
 * @param {frappe.ui.form.Form} frm
 * @param {string} cdt
 * @param {string} cdn
 * @param {"revenue"|"cost"} side
 */
logistics.sync_air_charge_qty_for_unit_type_to_grid = function (frm, cdt, cdn, side) {
	if (!frm || !frm.doc || !cdt || !cdn || !locals[cdt] || !locals[cdt][cdn]) {
		return;
	}
	var row = locals[cdt][cdn];
	var is_cost = side === "cost";
	var method = is_cost ? row.cost_calculation_method : row.revenue_calculation_method;
	if (method && method !== "Per Unit") {
		return;
	}
	var ut = is_cost ? row.cost_unit_type : row.unit_type;
	if (!ut) {
		return;
	}
	var q = logistics.resolve_air_parent_quantity_by_unit_type(frm.doc, ut);
	var field = is_cost ? "cost_quantity" : "quantity";
	row._logistics_skip_charge_recalc = field;
	frappe.model.set_value(cdt, cdn, field, q);
	logistics.refresh_charge_grid_cell(frm, cdt, cdn, field);
	setTimeout(function () {
		if (row._logistics_skip_charge_recalc === field) {
			row._logistics_skip_charge_recalc = null;
		}
	}, 250);
};

/**
 * @deprecated Use sync_air_charge_qty_for_unit_type_to_grid — kept for any external callers.
 */
logistics.prefill_air_charge_qty_for_unit_type_change = function (frm, row, side) {
	if (!frm || !row) {
		return;
	}
	var cdn = row.name;
	if (!cdn) {
		return;
	}
	var cdt = row.doctype;
	logistics.sync_air_charge_qty_for_unit_type_to_grid(frm, cdt, cdn, side);
};
