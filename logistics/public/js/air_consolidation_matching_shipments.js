// Copyright (c) 2026, AgilaSoft and contributors
// Air Consolidation → filter grid + aligned shipments table (same shell as Sea Consolidation)

frappe.provide("logistics");

var ACM_DIALOG_TITLE = __("Aligned Air Shipments");

function _acm_pad(specs, n) {
	var out = specs.slice();
	while (out.length < n) {
		out.push({ placeholder: 1, label: __("Filter field") });
	}
	return out.slice(0, n);
}

function acm_route_fallback(frm) {
	var routes = frm.doc.consolidation_routes || [];
	if (!routes.length) {
		return null;
	}
	var o = frm.doc.origin_airport;
	var d = frm.doc.destination_airport;
	for (var i = 0; i < routes.length; i++) {
		var row = routes[i];
		if (!row) {
			continue;
		}
		if (o && d && row.origin_airport === o && row.destination_airport === d) {
			return row;
		}
	}
	return routes[0];
}

/** Route Date + Time → string for Datetime filter (matches server fallback). */
function acm_route_departure_value(rf) {
	if (!rf || !rf.departure_date) {
		return "";
	}
	var t = rf.departure_time || "";
	if (!t) {
		return rf.departure_date;
	}
	return String(rf.departure_date).trim() + " " + String(t).trim();
}

function acm_specs(frm) {
	var rf = acm_route_fallback(frm);
	var dep = frm.doc.departure_date || "";
	var airline = frm.doc.airline || "";
	var flight = frm.doc.flight_number || "";
	if (rf) {
		if (!dep) {
			dep = acm_route_departure_value(rf);
		}
		if (!airline && rf.airline) {
			airline = rf.airline;
		}
		if (!flight && rf.flight_number) {
			flight = rf.flight_number;
		}
	}
	return [
		{ key: "company", ft: "Link", opt: "Company", lbl: __("Company"), v: frm.doc.company || "" },
		{ key: "branch", ft: "Link", opt: "Branch", lbl: __("Branch"), v: frm.doc.branch || "" },
		{
			key: "origin_airport",
			ft: "Link",
			opt: "UNLOCO",
			lbl: __("Origin Airport"),
			v: frm.doc.origin_airport || "",
		},
		{
			key: "destination_airport",
			ft: "Link",
			opt: "UNLOCO",
			lbl: __("Destination Airport"),
			v: frm.doc.destination_airport || "",
		},
		{
			key: "target_departure",
			ft: "Datetime",
			lbl: __("Departure (strict date match)"),
			v: dep,
		},
		{
			key: "airline",
			ft: "Link",
			opt: "Airline",
			lbl: __("Airline"),
			v: airline,
		},
		{ key: "flight_number", ft: "Data", lbl: __("Flight"), v: flight },
	];
}

function acm_mount($grid, rawSpecs, dlg) {
	dlg._acm_ctrls = [];
	rawSpecs.forEach(function (spec, ix) {
		var $cell = $('<div class="logistics-gcfq-filter-cell">').appendTo($grid);
		if (spec.placeholder) {
			$cell.append(
				'<label class="logistics-gcfq-filter-label logistics-gcfq-filter-label--muted">' +
					__(spec.label) +
					"</label>"
			);
			$cell.append(
				'<input type="text" readonly class="form-control input-sm logistics-gcfq-filter-input" tabindex="-1" placeholder="—"/>'
			);
			return;
		}
		var df = {
			fieldname: "acm_fw_" + ix,
			fieldtype: spec.ft,
			options: spec.opt || "",
			label: "",
		};
		if (spec.opt === "Branch") {
			df.get_query = function () {
				var cmp = "";
				(dlg._acm_ctrls || []).forEach(function (x) {
					if (x.key === "company" && x.get_val) {
						cmp = (x.get_val() || "").trim();
					}
				});
				var f = [];
				if (cmp && frappe.meta.has_field("Branch", "custom_company")) {
					f.push(["Branch", "custom_company", "=", cmp]);
				}
				return { filters: f };
			};
		}
		var c = frappe.ui.form.make_control({ df: df, parent: $cell, render_input: true });
		c.set_value(spec.v || "");
		$cell.prepend($('<label class="logistics-gcfq-filter-label">').text(spec.lbl || ""));
		dlg._acm_ctrls.push({
			key: spec.key,
			get_val: function () {
				return c.get_value();
			},
			control: c,
		});
	});
}

function acm_snap(dlg) {
	var o = {};
	(dlg._acm_ctrls || []).forEach(function (x) {
		o[x.key] = x.get_val() == null ? "" : String(x.get_val()).trim();
	});
	dlg._acm_s0 = o;
}

function acm_overrides(dlg) {
	var cur = {};
	(dlg._acm_ctrls || []).forEach(function (x) {
		cur[x.key] = x.get_val() == null ? "" : String(x.get_val()).trim();
	});
	var s0 = dlg._acm_s0 || {};
	var out = {};
	Object.keys(cur).forEach(function (k) {
		if (!(k in s0) || cur[k] !== (s0[k] || "").trim()) {
			out[k] = cur[k];
		}
	});
	return out;
}

function acm_debounce_reload(dlg, reload) {
	var tmr;
	function go() {
		if (tmr) {
			clearTimeout(tmr);
		}
		tmr = setTimeout(reload, 350);
	}
	(dlg._acm_ctrls || []).forEach(function (x) {
		if (x.control && x.control.$wrapper) {
			x.control.$wrapper.on("change", go);
		}
	});
}

function acm_td_detail(rw) {
	var rt = rw.row_type || "";
	if (rt === "already") {
		return frappe.utils.escape_html(__("Already on planned list"));
	}
	if (rt === "blocked") {
		return frappe.utils.escape_html(String(rw.reason || __("Excluded")));
	}
	return frappe.utils.escape_html(__("Eligible"));
}

logistics.open_air_consolidation_matching_shipments_dialog = function (frm) {
	if (!frm || frm.doctype !== "Air Consolidation" || frm.doc.__islocal || !frm.doc.name) {
		frappe.msgprint(__("Save the consolidation first."));
		return;
	}
	if (frm.doc.docstatus !== 0) {
		frappe.msgprint(__("Only draft consolidations allow this action."));
		return;
	}
	if ((frm.doc.air_planning_status || "Draft") === "Submitted") {
		frappe.msgprint(__("Reset planning to draft before fetching shipments."));
		return;
	}

	var dlg = new frappe.ui.Dialog({
		title: ACM_DIALOG_TITLE,
		size: "large",
		no_focus: true,
		fields: [{ fieldtype: "HTML", fieldname: "acm_body", options: "<div class='acm-root'></div>" }],
		secondary_action_label: __("Close"),
		secondary_action: function () {
			dlg.hide();
		},
	});

	dlg.onhide = function () {
		(dlg._acm_ctrls || []).forEach(function (x) {
			if (x.control && x.control.$wrapper) {
				x.control.$wrapper.remove();
			}
		});
		dlg._acm_ctrls = [];
	};

	dlg.show();
	dlg.$wrapper.addClass("logistics-gcfq-dialog logistics-acm-dialog");

	var $shell = dlg.$wrapper.find(".acm-root");
	function loadMatches() {
		$shell.empty();
		var $top = $('<div class="acm-top-wrap">').appendTo($shell);
		var box = $('<div class="logistics-gcfq-filters">').appendTo($top);
		box.append($('<div class="logistics-gcfq-filters-title">').text(__("List filter criteria")));

		var grid = $('<div class="logistics-gcfq-filters-grid">').appendTo(box);
		acm_mount(grid, _acm_pad(acm_specs(frm), 8), dlg);
		var $act = $('<div class="gcfq-filter-actions">').appendTo(box);
		$('<button type="button" class="btn btn-sm btn-default">' + __("Apply filters") + "</button>")
			.appendTo($act)
			.on("click", function () {
				runList();
			});
		acm_debounce_reload(dlg, runList);

		var $list = $('<div class="acm-dynamic">').appendTo($shell);

		function runList() {
			$list.html("<p class=text-muted>" + __("Loading aligned shipments…") + "</p>");
			frappe.call({
				doc: frm.doc,
				method: "preview_matching_air_shipments",
				args: { filter_overrides: acm_overrides(dlg) },
				callback: function (r) {
					if (!r || r.exc) {
						$list.html('<div class="alert alert-danger">' + __("Failed to load.") + "</div>");
						return;
					}
					var P = r.message || {};
					if (P.error) {
						$list.html(
							'<div class="alert alert-warning">' +
								frappe.utils.escape_html(String(P.error)) +
								"</div>"
						);
						return;
					}
					var rows = Array.isArray(P.rows) ? P.rows : [];
					var banner =
						frappe.utils.escape_html(String(P.message || "")) ||
						frappe.utils.escape_html(__("No matching rows."));

					if (!rows.length) {
						$list.html(
							'<p class=text-muted acm-m-ban>' +
								frappe.utils.escape_html(__("No aligning Air Shipments for these criteria.")) +
								"</p>"
						);
						return;
					}

					var thead =
						'<thead><tr><th width="42"></th>' +
						"<th>" +
						frappe.utils.escape_html(__("Shipment")) +
						"</th>" +
						"<th>" +
						frappe.utils.escape_html(__("Job status")) +
						"</th>" +
						"<th>" +
						frappe.utils.escape_html(__("Route")) +
						"</th>" +
						"<th>" +
						frappe.utils.escape_html(__("ETD")) +
						"</th>" +
						"<th>" +
						frappe.utils.escape_html(__("Details")) +
						"</th></tr></thead>";

					function etdFmt(v) {
						if (!v) {
							return "—";
						}
						try {
							return frappe.datetime.str_to_user(String(v));
						} catch (e) {
							return String(v);
						}
					}

					var trs = "";
					rows.forEach(function (rw) {
						var elig = rw.row_type === "eligible";
						var chk = "";
						var nmEsc = frappe.utils.escape_html(String(rw.name || ""));
						if (elig && rw.name) {
							chk =
								'<input type="checkbox" class="acm-sel" data-sn="' +
								frappe.utils.escape_html(String(rw.name)) +
								'" aria-label="' +
								frappe.utils.escape_html(__("Select")) +
								'"/>';
						} else if (elig) {
							chk = '<input type="checkbox" class="acm-sel" />';
						} else {
							chk = '<input type="checkbox" disabled />';
						}
						var route =
							rw.origin_port && rw.destination_port
								? frappe.utils.escape_html(String(rw.origin_port)) +
								  " → " +
								  frappe.utils.escape_html(String(rw.destination_port))
								: "—";
						trs +=
							"<tr><td>" +
							chk +
							"</td><td>" +
							nmEsc +
							"</td><td>" +
							frappe.utils.escape_html(String(rw.job_status || "")) +
							"</td><td>" +
							route +
							"</td><td>" +
							frappe.utils.escape_html(etdFmt(rw.etd)) +
							'</td><td class="text-muted">' +
							acm_td_detail(rw) +
							"</td></tr>";
					});

					var html =
						'<p class="text-muted acm-m-ban">' +
						banner +
						'</p><div class="acm-m-toolbar">' +
						'<input type="search" class="form-control input-sm acm-search" placeholder="' +
						frappe.utils.escape_html(__("Search…")) +
						'"/>' +
						'<span class="acm-m-stat"></span>' +
						'<button type="button" class="btn btn-xs btn-default acm-sel-all">' +
						__("Select all addable") +
						"</button>" +
						'<button type="button" class="btn btn-sm btn-primary acm-apply">' +
						__("Add selected to planned list") +
						"</button></div>" +
						'<div class="logistics-gcfq-table-wrap" style="max-height:54vh;">' +
						'<table class="logistics-gcfq-table acm-tbl">' +
						thead +
						"<tbody>" +
						trs +
						"</tbody></table></div>";

					$list.html(html);

					var $tbl = $list.find(".acm-tbl");

					function stat() {
						var k = $list.find(".acm-sel:checked").length;
						$list.find(".acm-m-stat").text(
							__("{0} selected", [String(k)])
						);
					}

					$list.off(".acmacm");
					$list.on("change.acmacm", ".acm-sel", stat);
					stat();

					$list.find(".acm-sel-all").on("click", function () {
						$list.find(".acm-sel").prop("checked", true);
						stat();
					});

					$list.on("input.acmacm", ".acm-search", function () {
						var q = String($list.find(".acm-search").val() || "")
							.toLowerCase()
							.trim();
						$tbl.find("tbody tr").each(function () {
							var t = $(this).text().toLowerCase();
							$(this).toggle(!q || t.indexOf(q) !== -1);
						});
					});

					$list.find(".acm-apply").on("click", function () {
						var picked = [];
						$list.find(".acm-sel:checked").each(function () {
							var n = $(this).attr("data-sn");
							if (n) {
								picked.push(n);
							}
						});
						if (!picked.length) {
							frappe.msgprint(__("Select at least one eligible shipment."));
							return;
						}
						frappe.call({
							doc: frm.doc,
							method: "apply_selected_air_shipments_to_planning",
							args: {
								shipment_names: picked,
								filter_overrides: acm_overrides(dlg),
							},
							freeze: true,
							freeze_message: __("Updating…"),
							callback: function (r2) {
								if (!r2 || r2.exc) {
									return;
								}
								var m = (r2.message && r2.message.message) || __("Done.");
								dlg.hide();
								frappe.show_alert({ message: __(m), indicator: "green" }, 4);
								frm.reload_doc();
							},
						});
					});
				},
			});
		}

		setTimeout(function () {
			acm_snap(dlg);
			runList();
		}, 0);
	}

	loadMatches();
};
