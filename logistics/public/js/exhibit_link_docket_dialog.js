// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Add Dockets: pick tagged dockets and append to the Exhibit dockets table.

(function () {
	"use strict";

	function _esc(v) {
		return frappe.utils.escape_html(v == null ? "" : String(v));
	}

	function _formatDate(v) {
		if (!v) return "—";
		try {
			return frappe.datetime.str_to_user(String(v));
		} catch (e) {
			return String(v);
		}
	}

	function _gridDocketNames(frm) {
		return (frm.doc.dockets || [])
			.map(function (r) {
				return r.docket;
			})
			.filter(Boolean);
	}

	function _renderTable($wrap, rows, picked) {
		picked = picked || {};
		if (!rows.length) {
			$wrap.find(".epd-table-host").html(
				'<p class="text-muted epd-empty">' +
					_esc(__("No tagged dockets available to add.")) +
					"</p>"
			);
			return;
		}

		const thead =
			"<thead><tr>" +
			'<th style="width:36px"><input type="checkbox" class="epd-select-all" aria-label="' +
			_esc(__("Select all")) +
			'"/></th>' +
			"<th>" + _esc(__("Docket")) + "</th>" +
			"<th>" + _esc(__("Exhibitor")) + "</th>" +
			"<th>" + _esc(__("Booth")) + "</th>" +
			"<th>" + _esc(__("Status")) + "</th>" +
			"<th>" + _esc(__("Docket Date")) + "</th>" +
			"</tr></thead>";

		let trs = "";
		rows.forEach(function (rw) {
			const nm = rw.name || "";
			const checked = nm && picked[nm] ? " checked" : "";
			const chk =
				'<input type="checkbox" class="epd-sel" data-docket="' +
				_esc(nm) +
				'" aria-label="' +
				_esc(__("Select")) +
				'"' +
				checked +
				"/>";
			trs +=
				"<tr data-docket='" +
				_esc(nm) +
				"'>" +
				"<td>" +
				chk +
				"</td><td>" +
				_esc(nm) +
				"</td><td>" +
				_esc(rw.exhibitor_name || rw.exhibitor || "") +
				"</td><td>" +
				_esc(rw.booth_no || "") +
				"</td><td>" +
				_esc(rw.status || "") +
				"</td><td>" +
				_esc(_formatDate(rw.docket_date)) +
				"</td></tr>";
		});

		$wrap.find(".epd-table-host").html(
			'<div class="epd-scroll">' +
				'<table class="table table-bordered table-sm epd-table">' +
				thead +
				"<tbody>" +
				trs +
				"</tbody></table></div>"
		);

		const $all = $wrap.find(".epd-select-all");
		const $eligible = $wrap.find("input.epd-sel");
		$all.prop(
			"checked",
			$eligible.length > 0 && $eligible.filter(":checked").length === $eligible.length
		);
		$all.prop("disabled", $eligible.length === 0);

		$all.off("change.epd").on("change.epd", function () {
			const on = $(this).prop("checked");
			$eligible.prop("checked", on);
			$eligible.each(function () {
				const dn = $(this).attr("data-docket");
				if (on && dn) picked[dn] = true;
				else if (dn) delete picked[dn];
			});
		});

		$wrap.find("input.epd-sel").off("change.epd").on("change.epd", function () {
			const dn = $(this).attr("data-docket");
			if ($(this).prop("checked") && dn) picked[dn] = true;
			else if (dn) delete picked[dn];
			$all.prop(
				"checked",
				$eligible.length > 0 && $eligible.filter(":checked").length === $eligible.length
			);
		});
	}

	function _filterRows(rows, term) {
		const t = (term || "").trim().toLowerCase();
		if (!t) return rows;
		return rows.filter(function (rw) {
			const hay = [
				rw.name,
				rw.exhibitor,
				rw.exhibitor_name,
				rw.booth_no,
				rw.status,
			]
				.join(" ")
				.toLowerCase();
			return hay.indexOf(t) !== -1;
		});
	}

	function _loadRows(dlg, frm, search) {
		const $wrap = dlg.fields_dict.epd_body.$wrapper;
		$wrap.find(".epd-table-host").html(
			'<p class="text-muted">' + _esc(__("Loading dockets…")) + "</p>"
		);
		frappe.call({
			method:
				"logistics.mice.doctype.mice_project.mice_project.get_linkable_dockets_for_exhibit",
			args: {
				exhibit_name: frm.doc.name,
				search: search || "",
				limit: 100,
				exclude_dockets: _gridDocketNames(frm),
			},
			callback: function (r) {
				dlg._epd_all_rows = r.message || [];
				_renderTable($wrap, _filterRows(dlg._epd_all_rows, dlg._epd_search), dlg._epd_picked);
			},
		});
	}

	function _pickedNames(dlg) {
		const picked = dlg._epd_picked || {};
		return Object.keys(picked).filter(function (k) {
			return picked[k];
		});
	}

	function _appendToGrid(frm, dlg) {
		const names = _pickedNames(dlg);
		if (!names.length) {
			frappe.msgprint({
				title: __("Select Dockets"),
				message: __("Select at least one Docket to add."),
				indicator: "orange",
			});
			return;
		}

		const existing = {};
		(frm.doc.dockets || []).forEach(function (r) {
			if (r.docket) existing[r.docket] = true;
		});

		const byName = {};
		(dlg._epd_all_rows || []).forEach(function (rw) {
			if (rw.name) byName[rw.name] = rw;
		});

		let added = 0;
		names.forEach(function (nm) {
			if (existing[nm]) return;
			const rw = byName[nm];
			if (!rw) return;
			frm.add_child("dockets", {
				docket: rw.name,
				exhibitor: rw.exhibitor || "",
				exhibitor_name: rw.exhibitor_name || "",
				booth_no: rw.booth_no || "",
				status: rw.status || "",
				docket_date: rw.docket_date || "",
			});
			existing[nm] = true;
			added += 1;
		});

		if (!added) {
			frappe.msgprint({
				title: __("Nothing to add"),
				message: __("Selected dockets are already on the table."),
				indicator: "orange",
			});
			return;
		}

		frm.refresh_field("dockets");
		dlg.hide();
		frappe.show_alert(
			{
				message: __("{0} docket(s) added to the table.", [added]),
				indicator: "green",
			},
			5
		);
	}

	window.logistics_open_exhibit_link_docket_dialog = function (frm) {
		if (!frm || !frm.doc || frm.doc.__islocal || !frm.doc.name) {
			frappe.msgprint({
				message: __("Save this Exhibit before adding Dockets."),
				indicator: "orange",
			});
			return;
		}

		const exhibitLabel = frm.doc.project_name || frm.doc.name;

		const dlg = new frappe.ui.Dialog({
			title: __("Add Dockets"),
			size: "large",
			fields: [{ fieldname: "epd_body", fieldtype: "HTML", options: "<div class='epd-root'></div>" }],
			primary_action_label: __("Add to Table"),
			primary_action: function () {
				_appendToGrid(frm, dlg);
			},
		});

		dlg._epd_picked = {};
		dlg._epd_search = "";
		dlg._epd_all_rows = [];

		dlg.show();
		dlg.$wrapper.addClass("logistics-gcfq-dialog");

		const $root = dlg.fields_dict.epd_body.$wrapper.find(".epd-root");
		$root.empty();
		$root.append(
			$("<p>")
				.addClass("text-muted")
				.css({ fontSize: "12px", marginBottom: "10px" })
				.text(
					__(
						"Select dockets tagged on {0} to add to the table below.",
						[exhibitLabel]
					)
				)
		);
		const $toolbar = $("<div class='epd-toolbar'>").css({
			display: "flex",
			gap: "10px",
			marginBottom: "10px",
			flexWrap: "wrap",
			alignItems: "center",
		});
		const $search = $(
			"<input type='text' class='form-control input-sm' style='max-width:280px'>"
		).attr("placeholder", __("Search dockets…"));
		$toolbar.append($search);
		$toolbar.append(
			$("<button type='button' class='btn btn-sm btn-default'>")
				.text(__("Refresh"))
				.on("click", function () {
					_loadRows(dlg, frm, dlg._epd_search);
				})
		);
		$root.append($toolbar);
		$root.append($("<div class='epd-table-host'>"));
		$root.append(
			$("<style>")
				.text(
					".epd-scroll{max-height:min(52vh,480px);overflow:auto;}" +
						".epd-table{margin:0;background:var(--control-bg,#fff);}" +
						".epd-empty{padding:16px;text-align:center;}"
				)
		);

		let searchTimer = null;
		$search.on("input", function () {
			dlg._epd_search = $(this).val() || "";
			clearTimeout(searchTimer);
			searchTimer = setTimeout(function () {
				_renderTable(
					dlg.fields_dict.epd_body.$wrapper,
					_filterRows(dlg._epd_all_rows, dlg._epd_search),
					dlg._epd_picked
				);
			}, 200);
		});

		_loadRows(dlg, frm, "");
		setTimeout(function () {
			$search.trigger("focus");
		}, 80);
	};
})();
