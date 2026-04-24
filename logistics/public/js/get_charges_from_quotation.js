// Copyright (c) 2026, AgilaSoft and contributors
// Shared: Action → Get Charges from Quotation (Sea Booking, Air Booking, Transport Order, Declaration Order)

frappe.provide("logistics");

var GET_CHARGES_TITLE_LIST = __("Get Charges from Quotation");

/**
 * Open dialog: expandable cards per Sales Quote (charge preview) → Apply.
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

	if (frm.doctype === "Transport Order") {
		if (!frm.doc.location_from || !frm.doc.location_to) {
			frappe.msgprint(__("Set Location From and Location To before loading charges from a quotation."));
			return;
		}
	} else if (frm.doctype === "Declaration Order") {
		if (!frm.doc.customs_authority || !frm.doc.declaration_type || !frm.doc.customs_broker) {
			frappe.msgprint(
				__(
					"Set Customs Authority, Declaration Type, and Customs Broker before loading charges from a quotation."
				)
			);
			return;
		}
	} else if (frm.doctype === "Air Booking") {
		var hasOdpair = frm.doc.origin_port && frm.doc.destination_port;
		var hasAirline = (frm.doc.airline && String(frm.doc.airline).trim()) ? true : false;
		if (!hasOdpair && !hasAirline) {
			frappe.msgprint(
				__(
					"Set Origin Port and Destination Port, or set Airline, before loading charges from a quotation."
				)
			);
			return;
		}
	} else {
		if (!frm.doc.origin_port || !frm.doc.destination_port) {
			frappe.msgprint(__("Set Origin Port and Destination Port before loading charges from a quotation."));
			return;
		}
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

	d.show();
	d.$wrapper.addClass("logistics-gcfq-dialog");

	var $wrap = d.$wrapper.find(".quotation-list");
	$wrap.addClass("logistics-gcfq-quotation-list");
	_load_quote_list(frm, d, $wrap);
};

function _set_dialog_title(dialog, title) {
	if (dialog && dialog.set_title) {
		dialog.set_title(title);
	}
}

/** @param {Record<string, unknown>|null|undefined} filters */
function _gcfq_filters_criteria_html(filters) {
	if (!filters || typeof filters !== "object") {
		return "";
	}
	var st = filters.service_type != null ? String(filters.service_type) : "";
	var custLbl = filters.customer_label != null ? String(filters.customer_label) : "";
	var cust = filters.customer != null ? String(filters.customer) : "";
	var oLbl = filters.origin_label != null ? String(filters.origin_label) : "";
	var o = filters.origin != null ? String(filters.origin) : "";
	var dLbl = filters.destination_label != null ? String(filters.destination_label) : "";
	var dest = filters.destination != null ? String(filters.destination) : "";
	var extra = filters.extra_criteria;
	var airlineOnly =
		filters.airline_only_mode === true || filters.airline_only_mode === 1;
	var hasCorridor =
		(o && String(o).trim() !== "") || (dest && String(dest).trim() !== "");
	var open =
		'<div class="logistics-gcfq-filters">' +
		'<div class="logistics-gcfq-filters-title">' +
		__("List filter criteria") +
		"</div>" +
		'<dl class="logistics-gcfq-filters-dl">' +
		"<dt>" +
		__("Service type (from document)") +
		"</dt>" +
		"<dd>" +
		frappe.utils.escape_html(st) +
		"</dd>" +
		"<dt>" +
		frappe.utils.escape_html(custLbl) +
		"</dt>" +
		"<dd>" +
		frappe.utils.escape_html(cust) +
		"</dd>";

	function appendExtraRows() {
		if (!Array.isArray(extra) || !extra.length) {
			return;
		}
		extra.forEach(function (row) {
			if (!row || typeof row !== "object") {
				return;
			}
			var lbl = row.label != null ? String(row.label) : "";
			var val = row.value != null ? String(row.value) : "";
			mid +=
				"<dt>" +
				frappe.utils.escape_html(lbl) +
				"</dt><dd>" +
				frappe.utils.escape_html(val) +
				"</dd>";
		});
	}

	var mid = "";
	if (airlineOnly && Array.isArray(extra) && extra.length) {
		// e.g. Air Booking: only airline is used to narrow the list (ports not set)
		appendExtraRows();
	} else if (Array.isArray(extra) && extra.length && !hasCorridor) {
		// e.g. Declaration Order: customs fields from parent, no port corridor on payload
		appendExtraRows();
	} else if (Array.isArray(extra) && extra.length && hasCorridor) {
		// e.g. Air Booking: origin, destination, and airline all filter the list
		mid +=
			"<dt>" +
			frappe.utils.escape_html(oLbl) +
			"</dt>" +
			"<dd>" +
			frappe.utils.escape_html(o) +
			"</dd>" +
			"<dt>" +
			frappe.utils.escape_html(dLbl) +
			"</dt>" +
			"<dd>" +
			frappe.utils.escape_html(dest) +
			"</dd>";
		appendExtraRows();
	} else {
		mid +=
			"<dt>" +
			frappe.utils.escape_html(oLbl) +
			"</dt>" +
			"<dd>" +
			frappe.utils.escape_html(o) +
			"</dd>" +
			"<dt>" +
			frappe.utils.escape_html(dLbl) +
			"</dt>" +
			"<dd>" +
			frappe.utils.escape_html(dest) +
			"</dd>";
	}
	return open + mid + "</dl></div>";
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
		'<div class="logistics-gcfq-filters logistics-gcfq-filters--below-cards">',
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

function _gcfq_load_card_preview($pv, frm, sales_quote, onDone) {
	$pv.removeData("gcfq-charges-count");
	$pv.html(_gcfq_card_loading_html());
	frappe.call({
		method: "logistics.utils.get_charges_from_quotation.preview_quotation_charges_for_job",
		args: { doctype: frm.doctype, docname: frm.doc.name, sales_quote: sales_quote },
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
			frappe.call({
				method: "logistics.utils.get_charges_from_quotation.apply_quotation_charges_to_job",
				args: {
					doctype: frm.doctype,
					docname: frm.doc.name,
					sales_quote: sales_quote,
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
		_gcfq_load_card_preview($pv, frm, sq, function (cnt) {
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
			_gcfq_load_card_preview($pv, frm, sq, function (cnt) {
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

function _load_quote_list(frm, dialog, $wrap) {
	_set_dialog_title(dialog, GET_CHARGES_TITLE_LIST);
	$wrap.html('<p class="text-muted">' + __("Loading quotations…") + "</p>");

	frappe.call({
		method: "logistics.utils.get_charges_from_quotation.list_sales_quotes_for_job",
		args: { doctype: frm.doctype, docname: frm.doc.name },
		callback: function (r) {
			if (!r || r.exc) {
				$wrap.html('<div class="alert alert-danger">' + __("Failed to load quotations.") + "</div>");
				return;
			}
			var msg = (r.message && r.message.message) || "";
			var quotes = (r.message && r.message.quotes) || [];
			var filters = r.message && r.message.filters;
			var criteriaHtml = _gcfq_filters_criteria_html(filters);
			var rulesHtml = _gcfq_filters_rules_html(filters);

			if (!quotes.length) {
				$wrap.html(
					criteriaHtml +
						'<div class="alert alert-warning">' +
						frappe.utils.escape_html(msg || __("No matching Sales Quotes found.")) +
						"</div>" +
						rulesHtml
				);
				return;
			}

			var $root = $('<div class="logistics-gcfq-list-root">');
			if (criteriaHtml) {
				$root.append(criteriaHtml);
			}

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

			$wrap.empty().append($root);
			_gcfq_bind_quote_cards($wrap, frm, dialog);
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
