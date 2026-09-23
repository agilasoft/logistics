// Copyright (c) 2026, AgilaSoft and contributors
// Action → Get Charges from Tariff (Sea Booking, Air Booking)

frappe.provide("logistics");

var GET_CHARGES_TITLE_TARIFF = __("Get Charges from Tariff");
var GCFT_FILTER_GRID_SLOTS = 8;

function _gcft_readonly_party_label(frm) {
	if (!frm || !frm.doc) {
		return "";
	}
	return (frm.doc.local_customer_name || frm.doc.local_customer || "").trim();
}

function _gcft_filter_specs(frm) {
	if (frm.doctype === "Sea Booking") {
		return [
			{ key: "_svc", readonly: true, label: __("Main Service"), value: __("Sea") },
			{
				key: "_cust",
				readonly: true,
				label: __("Local Customer"),
				value: _gcft_readonly_party_label(frm),
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
		];
	}
	if (frm.doctype === "Air Booking") {
		return [
			{ key: "_svc", readonly: true, label: __("Main Service"), value: __("Air") },
			{
				key: "_cust",
				readonly: true,
				label: __("Local Customer"),
				value: _gcft_readonly_party_label(frm),
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
		];
	}
	return [];
}

function _gcft_pad_specs(specs, n) {
	var out = specs.slice();
	while (out.length < n) {
		out.push({ placeholder: true, readonly: true, label: __("Filter field"), value: "", key: null });
	}
	return out.slice(0, n);
}

function _gcft_mount_filter_cell($grid, spec, frm, dialog, idx) {
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
		dialog._gcft_filter_controls.push({
			key: spec.key,
			read_only: true,
			get_value: function () {
				return spec.value || "";
			},
		});
		return;
	}
	var df = {
		fieldname: "gcft_filter_" + idx,
		label: "",
		fieldtype: spec.fieldtype,
		options: spec.options || "",
	};
	var ctrl = frappe.ui.form.make_control({ df: df, parent: $cell, render_input: true });
	ctrl.set_value(spec.value || "");
	dialog._gcft_filter_controls.push({
		key: spec.key,
		read_only: false,
		get_value: function () {
			return ctrl.get_value();
		},
		control: ctrl,
	});
}

function _gcft_filter_value_from_frm(frm, key) {
	if (!frm || !frm.doc || !key) {
		return "";
	}
	var v = frm.doc[key];
	return v == null ? "" : String(v).trim();
}

function _gcft_capture_initial_filter_snapshot(dialog, frm) {
	dialog._gcft_initial_filter_values = {};
	(dialog._gcft_filter_controls || []).forEach(function (c) {
		if (!c.key || c.key.charAt(0) === "_") {
			return;
		}
		if (c.read_only) {
			return;
		}
		var v = frm && c.key ? _gcft_filter_value_from_frm(frm, c.key) : c.get_value();
		dialog._gcft_initial_filter_values[c.key] = v == null ? "" : String(v).trim();
	});
}

function _gcft_collect_filter_overrides(dialog) {
	var o = {};
	var init = dialog._gcft_initial_filter_values || {};
	(dialog._gcft_filter_controls || []).forEach(function (c) {
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

function _gcft_mount_filter_panel($parent, frm, dialog, reloadList) {
	$parent.empty();
	dialog._gcft_filter_controls = [];
	var $box = $('<div class="logistics-gcfq-filters">').appendTo($parent);
	$box.append($('<div class="logistics-gcfq-filters-title">').text(__("List filter criteria")));
	var $grid = $('<div class="logistics-gcfq-filters-grid">').appendTo($box);
	var specs = _gcft_pad_specs(_gcft_filter_specs(frm), GCFT_FILTER_GRID_SLOTS);
	specs.forEach(function (spec, idx) {
		_gcft_mount_filter_cell($grid, spec, frm, dialog, idx);
	});
	var timer;
	function schedule() {
		if (!dialog._gcft_ready) {
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
	(dialog._gcft_filter_controls || []).forEach(function (c) {
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

logistics.should_show_get_charges_from_tariff = function (frm) {
	if (!frm || !frm.doc) {
		return false;
	}
	if (frm.doctype !== "Sea Booking" && frm.doctype !== "Air Booking") {
		return false;
	}
	var as_int =
		typeof cint === "function"
			? cint
			: function (v) {
					return parseInt(v, 10) || 0;
				};
	if (frm.doc.__islocal) {
		return false;
	}
	if (as_int(frm.doc.docstatus) !== 0) {
		return false;
	}
	if (as_int(frm.doc.is_internal_job)) {
		return false;
	}
	if (
		window.logistics &&
		typeof logistics.job_linked_sales_quote_name === "function" &&
		logistics.job_linked_sales_quote_name(frm)
	) {
		return false;
	}
	if (
		window.logistics &&
		typeof logistics.job_should_hide_get_charges_from_quotation === "function" &&
		logistics.job_should_hide_get_charges_from_quotation(frm)
	) {
		return false;
	}
	return true;
};

logistics.add_get_charges_from_tariff_button_if_allowed = function (frm) {
	if (
		!window.logistics ||
		typeof logistics.should_show_get_charges_from_tariff !== "function" ||
		!logistics.should_show_get_charges_from_tariff(frm)
	) {
		return;
	}
	if (window.logistics && logistics.menu) {
		logistics.menu.add(frm, {
			label: __("Get Charges from Tariff"),
			group: __("Action"),
			ptype: "write",
			action: function () {
				if (logistics.open_get_charges_from_tariff_dialog) {
					logistics.open_get_charges_from_tariff_dialog(frm);
				}
			},
		});
		return;
	}
	frm.add_custom_button(__("Get Charges from Tariff"), function () {
		if (logistics.open_get_charges_from_tariff_dialog) {
			logistics.open_get_charges_from_tariff_dialog(frm);
		}
	}, __("Action"));
};

function _gcft_preview_inner_html(m) {
	if (!m || typeof m !== "object") {
		return '<div class="logistics-gcfq-preview-empty">' + __("Preview failed.") + "</div>";
	}
	if (m.error) {
		return (
			'<div class="alert alert-danger mb-0">' + frappe.utils.escape_html(String(m.error)) + "</div>"
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
			__("No charge lines to show for this tariff.") +
			"</div></div>";
		return lines;
	}
	lines +=
		'<div class="logistics-gcfq-table-wrap logistics-gcfq-preview-table-wrap">' +
		'<table class="logistics-gcfq-table logistics-gcfq-preview-table">' +
		"<thead><tr><th>" +
		__("Service type") +
		"</th><th>" +
		__("Item code") +
		"</th><th>" +
		__("Item name") +
		"</th><th class='gcfq-preview-th-rate'>" +
		__("Unit rate") +
		"</th></tr></thead><tbody>";
	charges.slice(0, 40).forEach(function (c) {
		if (!c) {
			return;
		}
		var raw =
			c.unit_rate !== undefined && c.unit_rate !== null && c.unit_rate !== ""
				? c.unit_rate
				: c.rate;
		var rateCell = raw != null && raw !== "" ? frappe.utils.escape_html(String(raw)) : "—";
		lines +=
			"<tr><td>" +
			frappe.utils.escape_html(String(c.service_type || "")) +
			"</td><td>" +
			frappe.utils.escape_html(String(c.item_code || "")) +
			"</td><td>" +
			frappe.utils.escape_html(String(c.item_name || "")) +
			"</td><td>" +
			rateCell +
			"</td></tr>";
	});
	lines += "</tbody></table></div></div>";
	return lines;
}

function _gcft_load_card_preview($pv, frm, tariff_name, dialog, onDone) {
	$pv.html(
		'<div class="gcfq-card-loading"><span class="gcfq-card-loading-spin"></span><span>' +
			__("Loading charge preview…") +
			"</span></div>"
	);
	frappe.call({
		method: "logistics.utils.get_charges_from_tariff.preview_tariff_charges_for_job",
		args: {
			doctype: frm.doctype,
			docname: frm.doc.name,
			tariff_name: tariff_name,
			filter_overrides: _gcft_collect_filter_overrides(dialog),
		},
		callback: function (r) {
			var m = (r && r.message) || {};
			$pv.html(_gcft_preview_inner_html(m));
			var cnt = 0;
			if (!m.error) {
				cnt = m.charges_count != null ? m.charges_count : (m.charges || []).length;
			}
			$pv.data("gcft-charges-count", cnt);
			if (onDone) {
				onDone(cnt);
			}
		},
		error: function () {
			$pv.html('<div class="alert alert-danger mb-0">' + __("Preview failed.") + "</div>");
			if (onDone) {
				onDone(0);
			}
		},
	});
}

function _gcft_apply_tariff(frm, tariff_name, dialog) {
	frappe.confirm(
		__(
			"Apply charges from Tariff {0}? Existing charge lines will be replaced.",
			[tariff_name]
		),
		function () {
			frappe.call({
				method: "logistics.utils.get_charges_from_tariff.apply_tariff_charges_to_job",
				args: {
					doctype: frm.doctype,
					docname: frm.doc.name,
					tariff_name: tariff_name,
					filter_overrides: _gcft_collect_filter_overrides(dialog),
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

function _gcft_bind_cards($wrap, frm, dialog) {
	$wrap.off(".gcft");
	$wrap.on("click.gcft", ".gcfq-card-toggle", function () {
		var $card = $(this).closest(".gcfq-card");
		$card.toggleClass("open");
		if (!$card.hasClass("open")) {
			return;
		}
		var $pv = $card.find(".gcfq-card-preview");
		if ($pv.data("gcft-loaded")) {
			return;
		}
		var tn = $card.attr("data-tariff-name") || "";
		var $btn = $card.find(".gcfq-card-apply");
		_gcft_load_card_preview($pv, frm, tn, dialog, function (cnt) {
			$pv.data("gcft-loaded", true);
			$btn.prop("disabled", !cnt);
		});
	});
	$wrap.on("click.gcft", ".gcfq-card-apply", function (e) {
		e.preventDefault();
		e.stopPropagation();
		var $card = $(this).closest(".gcfq-card");
		var tn = $card.attr("data-tariff-name") || "";
		var $pv = $card.find(".gcfq-card-preview");
		if (!$pv.data("gcft-loaded")) {
			$card.addClass("open");
			var $btn = $(this);
			_gcft_load_card_preview($pv, frm, tn, dialog, function (cnt) {
				$pv.data("gcft-loaded", true);
				$btn.prop("disabled", !cnt);
				if (cnt) {
					_gcft_apply_tariff(frm, tn, dialog);
				}
			});
			return;
		}
		if (!$pv.data("gcft-charges-count")) {
			frappe.msgprint(__("No charge lines to apply for this tariff."));
			return;
		}
		_gcft_apply_tariff(frm, tn, dialog);
	});
}

function _gcft_load_tariff_list(frm, dialog, $dynamic) {
	$dynamic.html('<p class="text-muted">' + __("Loading tariffs…") + "</p>");
	frappe.call({
		method: "logistics.utils.get_charges_from_tariff.list_tariffs_for_job",
		args: {
			doctype: frm.doctype,
			docname: frm.doc.name,
			filter_overrides: _gcft_collect_filter_overrides(dialog),
		},
		callback: function (r) {
			dialog._gcft_ready = true;
			if (!r || r.exc) {
				$dynamic.html('<div class="alert alert-danger">' + __("Failed to load tariffs.") + "</div>");
				return;
			}
			var msg = (r.message && r.message.message) || "";
			var tariffs = (r.message && r.message.tariffs) || [];
			if (!tariffs.length) {
				$dynamic.html(
					'<div class="alert alert-warning logistics-gcfq-status-alert mb-0">' +
						frappe.utils.escape_html(msg || __("No matching tariffs found.")) +
						"</div>"
				);
				return;
			}
			var $cards = $('<div class="gcfq-cards">');
			tariffs.forEach(function (row) {
				var tn = row.name || "";
				var title = row.tariff_name || tn;
				var $card = $('<div class="gcfq-card">').attr("data-tariff-name", tn);
				var $hd = $('<div class="gcfq-card-hd">');
				var $toggle = $('<div class="gcfq-card-toggle" role="button" tabindex="0">');
				$toggle.append($('<span class="gcfq-card-chevron">').text("\u25B8"));
				var $block = $('<div class="gcfq-card-head-block">');
				$block.append($('<span class="gcfq-card-mono-icon">').text((title || "?").charAt(0).toUpperCase()));
				var $text = $('<div class="gcfq-card-head-text">');
				$text.append($('<div class="gcfq-card-head-title">').text(title));
				var sub = [row.tariff_type || "", row.valid_from || "", row.valid_to || ""]
					.filter(function (x) {
						return String(x || "").trim();
					})
					.join(" · ");
				if (sub) {
					$text.append($('<div class="gcfq-card-head-row2">').append($('<span class="gcfq-card-sub">').text(sub)));
				}
				$block.append($text);
				$toggle.append($block);
				var $apply = $("<button type='button'>")
					.addClass("btn btn-primary btn-sm gcfq-card-apply")
					.prop("disabled", true)
					.text(__("Apply"));
				$hd.append($toggle).append($apply);
				var $bd = $('<div class="gcfq-card-bd">').append($('<div class="gcfq-card-preview">'));
				$card.append($hd).append($bd);
				$cards.append($card);
			});
			$dynamic.empty().append($('<div class="gcfq-cards-scroll">').append($cards));
			_gcft_bind_cards($dynamic, frm, dialog);
		},
	});
}

logistics.open_get_charges_from_tariff_dialog = function (frm) {
	if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
		frappe.msgprint(__("Save the document first."));
		return;
	}
	if (!logistics.should_show_get_charges_from_tariff(frm)) {
		frappe.msgprint(
			__(
				"Get Charges from Tariff is not available (e.g. Sales Quote already linked, internal job, or submitted document)."
			)
		);
		return;
	}
	if (!frm.doc.local_customer) {
		frappe.msgprint(__("Set Local Customer first."));
		return;
	}
	var d = new frappe.ui.Dialog({
		title: GET_CHARGES_TITLE_TARIFF,
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
	d._gcft_ready = false;
	function reloadList() {
		_gcft_load_tariff_list(frm, d, $dynamic);
	}
	_gcft_mount_filter_panel($filterMount, frm, d, reloadList);
	setTimeout(function () {
		_gcft_capture_initial_filter_snapshot(d, frm);
		reloadList();
	}, 0);
};
