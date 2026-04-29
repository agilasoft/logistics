// Copyright (c) 2026, AgilaSoft and contributors
// Sea Consolidation → filter grid + aligned shipments table (same shell as Get Charges from Quotation)

frappe.provide("logistics");

var SCM_DIALOG_TITLE = __("Aligned Sea Shipments");

function _scm_pad(specs, n) {
	var out = specs.slice();
	while (out.length < n) {
		out.push({ placeholder: 1, label: __("Filter field") });
	}
	return out.slice(0, n);
}

function scm_specs(frm) {
	return [
		{ key: "company", ft: "Link", opt: "Company", lbl: __("Company"), v: frm.doc.company || "" },
		{ key: "branch", ft: "Link", opt: "Branch", lbl: __("Branch"), v: frm.doc.branch || "" },
		{
			key: "origin_port",
			ft: "Link",
			opt: "UNLOCO",
			lbl: __("Origin Port"),
			v: frm.doc.origin_port || "",
		},
		{
			key: "destination_port",
			ft: "Link",
			opt: "UNLOCO",
			lbl: __("Destination Port"),
			v: frm.doc.destination_port || "",
		},
		{
			key: "target_etd",
			ft: "Datetime",
			lbl: __("ETD (strict date match)"),
			v: frm.doc.etd || "",
		},
		{
			key: "shipping_line",
			ft: "Link",
			opt: "Shipping Line",
			lbl: __("Shipping Line"),
			v: frm.doc.shipping_line || "",
		},
		{ key: "vessel_name", ft: "Data", lbl: __("Vessel"), v: frm.doc.vessel_name || "" },
		{ key: "voyage_number", ft: "Data", lbl: __("Voyage"), v: frm.doc.voyage_number || "" },
	];
}

function scm_mount($grid, rawSpecs, dlg) {
	dlg._scm_ctrls = [];
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
			fieldname: "scm_fw_" + ix,
			fieldtype: spec.ft,
			options: spec.opt || "",
			label: "",
		};
		if (spec.opt === "Branch") {
			// Avoid Branch.disabled in filters — search_link enforces field permissions on filter fields.
			df.get_query = function () {
				var cmp = "";
				(dlg._scm_ctrls || []).forEach(function (x) {
					if (x.key === "company" && x.get_val) {
						cmp = (x.get_val() || "").trim();
					}
				});
				var f = [];
				if (cmp) {
					f.push(["Branch", "company", "=", cmp]);
				}
				return { filters: f };
			};
		}
		var c = frappe.ui.form.make_control({ df: df, parent: $cell, render_input: true });
		c.set_value(spec.v || "");
		$cell.prepend($('<label class="logistics-gcfq-filter-label">').text(spec.lbl || ""));
		dlg._scm_ctrls.push({
			key: spec.key,
			get_val: function () {
				return c.get_value();
			},
			control: c,
		});
	});
}

function scm_snap(dlg) {
	var o = {};
	(dlg._scm_ctrls || []).forEach(function (x) {
		o[x.key] = x.get_val() == null ? "" : String(x.get_val()).trim();
	});
	dlg._scm_s0 = o;
}

function scm_overrides(dlg) {
	var cur = {};
	(dlg._scm_ctrls || []).forEach(function (x) {
		cur[x.key] = x.get_val() == null ? "" : String(x.get_val()).trim();
	});
	var s0 = dlg._scm_s0 || {};
	var out = {};
	Object.keys(cur).forEach(function (k) {
		if (!(k in s0) || cur[k] !== (s0[k] || "").trim()) {
			out[k] = cur[k];
		}
	});
	return out;
}

function scm_debounce_reload(dlg, reload) {
	var tmr;
	function go() {
		if (tmr) {
			clearTimeout(tmr);
		}
		tmr = setTimeout(reload, 350);
	}
	(dlg._scm_ctrls || []).forEach(function (x) {
		if (x.control && x.control.$wrapper) {
			x.control.$wrapper.on("change", go);
		}
	});
}

function scm_td_detail(rw) {
	var rt = rw.row_type || "";
	if (rt === "already") {
		return frappe.utils.escape_html(__("Already on planned list"));
	}
	if (rt === "blocked") {
		return frappe.utils.escape_html(String(rw.reason || __("Excluded")));
	}
	return frappe.utils.escape_html(__("Eligible"));
}

logistics.open_sea_consolidation_matching_shipments_dialog = function (frm) {
	if (!frm || frm.doctype !== "Sea Consolidation" || frm.doc.__islocal || !frm.doc.name) {
		frappe.msgprint(__("Save the consolidation first."));
		return;
	}
	if (frm.doc.docstatus !== 0) {
		frappe.msgprint(__("Only draft consolidations allow this action."));
		return;
	}
	if ((frm.doc.sea_planning_status || "Draft") === "Submitted") {
		frappe.msgprint(__("Reset planning to draft before fetching shipments."));
		return;
	}

	var dlg = new frappe.ui.Dialog({
		title: SCM_DIALOG_TITLE,
		size: "large",
		no_focus: true,
		fields: [{ fieldtype: "HTML", fieldname: "scm_body", options: "<div class='scm-root'></div>" }],
		secondary_action_label: __("Close"),
		secondary_action: function () {
			dlg.hide();
		},
	});

	dlg.onhide = function () {
		(dlg._scm_ctrls || []).forEach(function (x) {
			if (x.control && x.control.$wrapper) {
				x.control.$wrapper.remove();
			}
		});
		dlg._scm_ctrls = [];
	};

	dlg.show();
	dlg.$wrapper.addClass("logistics-gcfq-dialog logistics-scm-dialog");

	var $shell = dlg.$wrapper.find(".scm-root");
	function loadMatches() {
		$shell.empty();
		var $top = $('<div class="scm-top-wrap">').appendTo($shell);
		var box = $('<div class="logistics-gcfq-filters">').appendTo($top);
		box.append($('<div class="logistics-gcfq-filters-title">').text(__("List filter criteria")));

		var grid = $('<div class="logistics-gcfq-filters-grid">').appendTo(box);
		scm_mount(grid, _scm_pad(scm_specs(frm), 8), dlg);
		var $act = $('<div class="gcfq-filter-actions">').appendTo(box);
		$('<button type="button" class="btn btn-sm btn-default">' + __("Apply filters") + "</button>")
			.appendTo($act)
			.on("click", function () {
				runList();
			});
		scm_debounce_reload(dlg, runList);

		var $list = $('<div class="scm-dynamic">').appendTo($shell);

		function runList() {
			$list.html("<p class=text-muted>" + __("Loading aligned shipments…") + "</p>");
			frappe.call({
				doc: frm.doc,
				method: "preview_matching_sea_shipments",
				args: { filter_overrides: scm_overrides(dlg) },
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
							'<p class=text-muted scm-m-ban>' +
								frappe.utils.escape_html(__("No aligning Sea Shipments for these criteria.")) +
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
								'<input type="checkbox" class="scm-sel" data-sn="' +
								frappe.utils.escape_html(String(rw.name)) +
								'" aria-label="' +
								frappe.utils.escape_html(__("Select")) +
								'"/>';
						} else if (elig) {
							chk = '<input type="checkbox" class="scm-sel" />';
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
							scm_td_detail(rw) +
							"</td></tr>";
					});

					var html =
						'<p class="text-muted scm-m-ban">' +
						banner +
						'</p><div class="scm-m-toolbar">' +
						'<input type="search" class="form-control input-sm scm-search" placeholder="' +
						frappe.utils.escape_html(__("Search…")) +
						'"/>' +
						'<span class="scm-m-stat"></span>' +
						'<button type="button" class="btn btn-xs btn-default scm-sel-all">' +
						__("Select all addable") +
						"</button>" +
						'<button type="button" class="btn btn-sm btn-primary scm-apply">' +
						__("Add selected to planned list") +
						"</button></div>" +
						'<div class="logistics-gcfq-table-wrap" style="max-height:54vh;">' +
						'<table class="logistics-gcfq-table scm-tbl">' +
						thead +
						"<tbody>" +
						trs +
						"</tbody></table></div>";

					$list.html(html);

					var $tbl = $list.find(".scm-tbl");

					function stat() {
						var k = $list.find(".scm-sel:checked").length;
						$list.find(".scm-m-stat").text(
							__("{0} selected", [String(k)])
						);
					}

					$list.off(".scmscm");
					$list.on("change.scmscm", ".scm-sel", stat);
					stat();

					$list.find(".scm-sel-all").on("click", function () {
						$list.find(".scm-sel").prop("checked", true);
						stat();
					});

					$list.on("input.scmscm", ".scm-search", function () {
						var q = String($list.find(".scm-search").val() || "")
							.toLowerCase()
							.trim();
						$tbl.find("tbody tr").each(function () {
							var t = $(this).text().toLowerCase();
							$(this).toggle(!q || t.indexOf(q) !== -1);
						});
					});

					$list.find(".scm-apply").on("click", function () {
						var picked = [];
						$list.find(".scm-sel:checked").each(function () {
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
							method: "apply_selected_sea_shipments_to_planning",
							args: {
								shipment_names: picked,
								filter_overrides: scm_overrides(dlg),
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
			scm_snap(dlg);
			runList();
		}, 0);
	}

	loadMatches();
};
