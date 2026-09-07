/*!
 * Change Request Dashboard tab (dashboard_html).
 * Diff view: Change Summary tiles, Field Changes, Row Changes.
 */
frappe.provide("logistics.change_request_summary");

(function () {
	"use strict";

	const SECTION_TABS = {
		Parties: "parties_tab",
		"Places & Dates": "places_tab",
		Packages: "packages_tab",
		Charges: "charges_tab",
		Notes: "notes_tab",
		Services: "services_tab",
	};

	const SECTION_FIELDS = {
		Parties: [
			"customer",
			"local_customer",
			"booking_party",
			"shipper",
			"consignee",
			"shipper_address",
			"consignee_address",
			"shipper_contact",
			"consignee_contact",
			"notify_party",
			"notify_party_address",
			"freight_agent",
			"sending_agent",
			"receiving_agent",
			"broker",
			"controlling_party",
			"incoterm",
			"direction",
			"house_type",
			"release_type",
			"entry_type",
			"service_level",
			"logistics_service_level",
		],
		"Places & Dates": [
			"origin_port",
			"destination_port",
			"etd",
			"eta",
			"scheduled_date",
			"booking_date",
			"vehicle_type",
			"transport_mode",
			"load_type",
			"transport_company",
			"transport_job_type",
			"container_type",
			"container_no",
			"run_date",
			"run_type",
			"route_name",
			"vehicle",
			"driver",
			"trailer_type",
			"dispatch_terminal",
			"return_terminal",
			"estimated_completion_time",
			"estimated_dispatch_datetime",
			"estimated_return_datetime",
			"transport_consolidation",
		],
		Notes: [
			"internal_notes",
			"client_notes",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
			"description",
			"marks_and_nos",
			"customer_ref_no",
			"dispatcher",
			"return_inspector",
			"remarks",
		],
	};

	const PACKAGE_COMPARE_FIELDS = [
		"commodity",
		"hs_code",
		"no_of_packs",
		"quantity",
		"uom",
		"weight",
		"volume",
		"length",
		"width",
		"height",
	];

	const LAYOUT_SKIP_FIELDTYPES = {
		"Tab Break": true,
		"Section Break": true,
		"Column Break": true,
		HTML: true,
		Button: true,
		Fold: true,
		Heading: true,
		Table: true,
		"Table MultiSelect": true,
	};

	/** Cache: job_type → { by_field, tabs: [{label, sections: [{label, fields[]}]}] } */
	const _job_layout_cache = {};

	function esc(v) {
		return frappe.utils && frappe.utils.escape_html
			? frappe.utils.escape_html(cstr(v))
			: $("<div>").text(cstr(v)).html();
	}

	function cstr(v) {
		if (v === null || v === undefined) return "";
		return String(v);
	}

	function display_val(v) {
		const s = cstr(v).trim();
		return s || "—";
	}

	function parse_baseline(frm) {
		try {
			return JSON.parse(frm.doc.baseline_json || "{}") || {};
		} catch (e) {
			return {};
		}
	}

	function field_label(fn) {
		return (frappe.meta.get_label && frappe.meta.get_label("Change Request", fn)) || __(frappe.unscrub(fn));
	}

	function strip_html(html) {
		if (!html) return "";
		const tmp = document.createElement("div");
		tmp.innerHTML = html;
		return (tmp.textContent || tmp.innerText || "").trim();
	}

	function normalize_for_compare(fn, v) {
		if (fn === "internal_notes" || fn === "client_notes" || fn === "remarks" || fn === "description") {
			return strip_html(v);
		}
		return cstr(v).trim();
	}

	/**
	 * Walk job DocType meta in field order → tab → section → fields.
	 * Used to group Field Changes like the shipment form.
	 */
	function build_job_field_layout(job_type) {
		job_type = cstr(job_type).trim();
		if (!job_type) return null;
		if (_job_layout_cache[job_type]) return _job_layout_cache[job_type];

		const meta = frappe.get_meta(job_type);
		if (!meta || !meta.fields || !meta.fields.length) return null;

		const by_name = {};
		meta.fields.forEach(function (df) {
			if (df && df.fieldname) by_name[df.fieldname] = df;
		});
		const field_order =
			meta.field_order && meta.field_order.length
				? meta.field_order
				: meta.fields.map(function (df) {
						return df.fieldname;
				  });

		const by_field = {};
		const tabs = [];
		let tab_idx = 0;
		let section_idx = 0;
		let tab = { label: __("Details"), sections: [] };
		let section = { label: "", key: tab_idx + ":0", fields: [] };
		tab.sections.push(section);
		tabs.push(tab);

		field_order.forEach(function (fn) {
			const df = by_name[fn];
			if (!df) return;
			const ft = df.fieldtype;
			if (ft === "Tab Break") {
				tab_idx += 1;
				section_idx = 0;
				tab = {
					label: cstr(df.label).trim() || __(frappe.unscrub(df.fieldname)),
					sections: [],
				};
				section = { label: "", key: tab_idx + ":" + section_idx, fields: [] };
				tab.sections.push(section);
				tabs.push(tab);
				return;
			}
			if (ft === "Section Break") {
				section_idx += 1;
				section = {
					label: cstr(df.label).trim(),
					key: tab_idx + ":" + section_idx,
					fields: [],
				};
				tab.sections.push(section);
				return;
			}
			if (LAYOUT_SKIP_FIELDTYPES[ft]) return;
			if (!df.fieldname) return;
			by_field[df.fieldname] = {
				tab: tab.label,
				section: section.label,
				section_key: section.key,
				fieldname: df.fieldname,
			};
			section.fields.push(df.fieldname);
		});

		const layout = { by_field: by_field, tabs: tabs };
		_job_layout_cache[job_type] = layout;
		return layout;
	}

	function ensure_job_layout(frm, done) {
		const job_type = cstr(frm.doc.job_type).trim();
		if (!job_type) {
			if (done) done(null);
			return;
		}
		const cached = build_job_field_layout(job_type);
		if (cached) {
			if (done) done(cached);
			return;
		}
		frappe.model.with_doctype(job_type, function () {
			if (done) done(build_job_field_layout(job_type));
		});
	}

	function layout_for_field(layout, fieldname, cr_section) {
		const hit = layout && layout.by_field && layout.by_field[fieldname];
		if (hit) {
			return {
				tab: hit.tab,
				form_section: hit.section || "",
				section_key: hit.section_key,
			};
		}
		return {
			tab: cr_section || __("Other"),
			form_section: "",
			section_key: "fallback:" + (cr_section || "Other"),
		};
	}

	function collect_field_diffs(frm) {
		const baseline = parse_baseline(frm);
		const header = (baseline && baseline.header) || {};
		const changed = [];
		const unchanged = [];
		const vis = logistics.change_request_visibility;
		const applicable =
			vis && vis.applicable_header_fields
				? vis.applicable_header_fields(frm.doc.job_type, frm.doc.change_sections)
				: null;
		const layout = build_job_field_layout(frm.doc.job_type);
		Object.keys(SECTION_FIELDS).forEach(function (section) {
			SECTION_FIELDS[section].forEach(function (fn) {
				if (applicable && !applicable[fn]) return;
				if (frm.doc[fn] === undefined) return;
				const from_v = normalize_for_compare(fn, header[fn]);
				const to_v = normalize_for_compare(fn, frm.doc[fn]);
				const place = layout_for_field(layout, fn, section);
				const row = {
					section: section,
					tab: place.tab,
					form_section: place.form_section,
					section_key: place.section_key,
					fieldname: fn,
					label: field_label(fn),
					from: from_v,
					to: to_v,
				};
				if (from_v !== to_v) changed.push(row);
				else unchanged.push(row);
			});
		});
		return { changed: changed, unchanged: unchanged, layout: layout };
	}

	/**
	 * Group diff rows by job form tab → section, preserving meta field order when possible.
	 */
	function group_rows_by_job_layout(rows, layout) {
		const groups = [];
		const group_index = {};

		function ensure_group(tab, form_section, section_key) {
			const key = section_key || tab + "\0" + form_section;
			if (group_index[key] !== undefined) return groups[group_index[key]];
			const g = {
				tab: tab,
				form_section: form_section,
				section_key: key,
				rows: [],
			};
			group_index[key] = groups.length;
			groups.push(g);
			return g;
		}

		if (layout && layout.tabs && layout.tabs.length) {
			const row_by_fn = {};
			rows.forEach(function (r) {
				row_by_fn[r.fieldname] = r;
			});
			layout.tabs.forEach(function (tab) {
				(tab.sections || []).forEach(function (sec) {
					const collected = [];
					(sec.fields || []).forEach(function (fn) {
						if (row_by_fn[fn]) {
							collected.push(row_by_fn[fn]);
							delete row_by_fn[fn];
						}
					});
					if (collected.length) {
						ensure_group(tab.label, sec.label || "", sec.key).rows = collected;
					}
				});
			});
			rows.forEach(function (r) {
				if (!row_by_fn[r.fieldname]) return;
				ensure_group(
					r.tab || r.section || __("Other"),
					r.form_section || "",
					r.section_key
				).rows.push(r);
			});
			return groups.filter(function (g) {
				return g.rows && g.rows.length;
			});
		}

		rows.forEach(function (r) {
			ensure_group(
				r.tab || r.section || __("Other"),
				r.form_section || "",
				r.section_key
			).rows.push(r);
		});
		return groups;
	}

	function base_pkg_map(baseline) {
		const map = {};
		((baseline && baseline.packages) || []).forEach(function (p) {
			map[cstr(p.source_row_name)] = p;
		});
		return map;
	}

	function package_row_changed(row, prev) {
		const action = cstr(row.row_action || "Update").trim();
		if (action === "Add" || action === "Remove") return true;
		for (let i = 0; i < PACKAGE_COMPARE_FIELDS.length; i++) {
			const fn = PACKAGE_COMPARE_FIELDS[i];
			if (cstr(prev[fn]) !== cstr(row[fn])) return true;
		}
		return false;
	}

	function section_counts(frm) {
		const baseline = parse_baseline(frm);
		const diffs = collect_field_diffs(frm);
		const by_section = { Parties: 0, "Places & Dates": 0, Notes: 0 };
		diffs.changed.forEach(function (r) {
			if (by_section[r.section] !== undefined) by_section[r.section] += 1;
		});
		const vis = logistics.change_request_visibility;
		const job_type = cstr(frm.doc.job_type);
		const pkgs = base_pkg_map(baseline);
		let pkg_n = 0;
		if (!vis || !vis.supports_packages || vis.supports_packages(job_type)) {
			(frm.doc.package_changes || []).forEach(function (row) {
				if (package_row_changed(row, pkgs[cstr(row.source_row_name)] || {})) pkg_n += 1;
			});
		}
		const charge_n =
			vis && vis.supports_charges && !vis.supports_charges(job_type)
				? 0
				: (frm.doc.charges || []).length;
		const service_n =
			vis && vis.supports_services && !vis.supports_services(job_type)
				? 0
				: (frm.doc.linked_services || []).length;
		return {
			Parties: by_section.Parties,
			"Places & Dates": by_section["Places & Dates"],
			Packages: pkg_n,
			Charges: charge_n,
			Notes: by_section.Notes,
			Services: service_n,
		};
	}

	function tile_meta(label) {
		const map = {
			Parties: { icon: "fa fa-users", unit: "fields" },
			"Places & Dates": { icon: "fa fa-calendar", unit: "fields" },
			Packages: { icon: "fa fa-cube", unit: "rows" },
			Charges: { icon: "fa fa-money", unit: "rows" },
			Notes: { icon: "fa fa-sticky-note-o", unit: "fields" },
		};
		return map[label] || { icon: "fa fa-circle-o", unit: "items" };
	}

	function unit_label(unit, n) {
		if (unit === "fields") return n === 1 ? __("Changed Field") : __("Changed Fields");
		if (unit === "rows") return n === 1 ? __("Changed Row") : __("Changed Rows");
		return __("Changed");
	}

	function render_tiles(counts) {
		const labels = ["Parties", "Places & Dates", "Packages", "Charges", "Notes"];
		let html = '<div class="cr-dash__tiles">';
		labels.forEach(function (label) {
			const meta = tile_meta(label);
			const n = cint(counts[label] || 0);
			html +=
				'<button type="button" class="cr-dash__tile" data-cr-section="' +
				esc(label) +
				'">' +
				'<span class="cr-dash__tile-icon"><i class="' +
				meta.icon +
				'"></i></span>' +
				'<span class="cr-dash__tile-body">' +
				'<span class="cr-dash__tile-count">' +
				n +
				"</span>" +
				'<span class="cr-dash__tile-sub">' +
				esc(unit_label(meta.unit, n)) +
				"</span>" +
				'<span class="cr-dash__tile-label">' +
				esc(__(label)) +
				"</span></span></button>";
		});
		html += "</div>";
		return html;
	}

	function can_edit_dashboard(frm) {
		if (cint(frm.doc.docstatus) !== 0 || frm.read_only) return false;
		if (frm.perm && frm.perm[0] && !frm.perm[0].write) return false;
		return true;
	}

	function val_box(kind, text) {
		return '<span class="cr-dash__val cr-dash__val--' + kind + '">' + esc(display_val(text)) + "</span>";
	}

	function proposed_cell_html(frm, r, is_changed) {
		const kind = is_changed ? "new" : "plain";
		const box = val_box(kind, r.to);
		if (!can_edit_dashboard(frm)) {
			return box;
		}
		return (
			'<button type="button" class="cr-dash__edit-proposed" data-cr-edit-field="' +
			esc(r.fieldname) +
			'" title="' +
			esc(__("Edit proposed value")) +
			'">' +
			box +
			' <i class="fa fa-pencil cr-dash__edit-icon"></i></button>'
		);
	}

	function status_cell_html(frm, r, is_changed) {
		let html = is_changed
			? '<span class="cr-dash__badge">' + esc(__("Changed")) + "</span>"
			: '<span class="cr-dash__badge cr-dash__badge--muted">' + esc(__("Unchanged")) + "</span>";
		if (can_edit_dashboard(frm) && is_changed) {
			html +=
				' <button type="button" class="cr-dash__revert" data-cr-revert-field="' +
				esc(r.fieldname) +
				'" title="' +
				esc(__("Revert to original")) +
				'">' +
				esc(__("Revert")) +
				"</button>";
		}
		return html;
	}

	function render_field_change_row(frm, r) {
		const is_changed = r.from !== r.to;
		return (
			"<tr" +
			(is_changed ? "" : ' class="cr-dash__row--unchanged"') +
			' data-cr-field="' +
			esc(r.fieldname) +
			'"><td class="cr-dash__field-name">' +
			esc(r.label) +
			"</td><td>" +
			val_box(is_changed ? "old" : "plain", r.from) +
			'</td><td class="cr-dash__arrow">→</td><td>' +
			proposed_cell_html(frm, r, is_changed) +
			'</td><td class="cr-dash__status-cell">' +
			status_cell_html(frm, r, is_changed) +
			"</td></tr>"
		);
	}

	function render_field_table(frm, rows) {
		let html =
			'<div class="cr-dash__table-wrap"><table class="cr-dash__table">' +
			"<thead><tr>" +
			"<th>" +
			esc(__("Field")) +
			"</th><th>" +
			esc(__("Original Value (From Job)")) +
			"</th><th></th><th>" +
			esc(__("Proposed Value (In Change Request)")) +
			"</th><th>" +
			esc(__("Status")) +
			"</th></tr></thead><tbody>";
		rows.forEach(function (r) {
			html += render_field_change_row(frm, r);
		});
		html += "</tbody></table></div>";
		return html;
	}

	function render_field_changes_grouped(frm, rows, layout) {
		const groups = group_rows_by_job_layout(rows, layout);
		if (!groups.length) return "";

		// Nest section groups under tab headings
		const by_tab = [];
		const tab_index = {};
		groups.forEach(function (g) {
			let bucket = tab_index[g.tab];
			if (bucket === undefined) {
				bucket = by_tab.length;
				tab_index[g.tab] = bucket;
				by_tab.push({ tab: g.tab, sections: [] });
			}
			by_tab[bucket].sections.push(g);
		});

		let html = "";
		by_tab.forEach(function (tab_group) {
			html +=
				'<div class="cr-dash__tab-group">' +
				'<h5 class="cr-dash__tab-title">' +
				esc(__(tab_group.tab)) +
				"</h5>";
			tab_group.sections.forEach(function (g) {
				html += '<div class="cr-dash__section-group">';
				if (g.form_section) {
					html +=
						'<h6 class="cr-dash__section-title">' +
						esc(__(g.form_section)) +
						"</h6>";
				}
				html += render_field_table(frm, g.rows) + "</div>";
			});
			html += "</div>";
		});
		return html;
	}

	function render_field_changes(frm, show_unchanged) {
		const diffs = collect_field_diffs(frm);
		const rows = show_unchanged ? diffs.changed.concat(diffs.unchanged) : diffs.changed;
		const n_changed = diffs.changed.length;
		const n_unchanged = diffs.unchanged.length;
		const editable = can_edit_dashboard(frm);

		let html =
			'<div class="cr-dash__card">' +
			'<div class="cr-dash__card-head">' +
			'<h4 class="cr-dash__card-title">' +
			esc(__("Field Changes")) +
			" (" +
			n_changed +
			")</h4>" +
			(editable
				? '<span class="cr-dash__hint">' + esc(__("Click a proposed value to edit")) + "</span>"
				: "") +
			"</div>";

		if (!rows.length && !show_unchanged) {
			html +=
				'<div class="cr-dash__empty">' +
				esc(__("No header field changes from the job baseline.")) +
				(editable && n_unchanged
					? ' <button type="button" class="cr-dash__link" data-cr-action="toggle-unchanged">' +
						esc(__("Show fields to edit")) +
						"</button>"
					: "") +
				"</div>";
		} else {
			html += render_field_changes_grouped(frm, rows, diffs.layout);
		}

		if (n_unchanged) {
			html +=
				'<button type="button" class="cr-dash__toggle-unchanged" data-cr-action="toggle-unchanged">' +
				(show_unchanged
					? esc(__("Hide unchanged fields ({0})", [n_unchanged]))
					: esc(__("Show unchanged fields ({0})", [n_unchanged]))) +
				"</button>";
		}
		html += "</div>";
		return html;
	}

	function dialog_fieldtype(df) {
		if (!df) return "Data";
		const ft = df.fieldtype;
		if (ft === "Text Editor" || ft === "HTML Editor") return "Text Editor";
		if (ft === "Long Text" || ft === "Text" || ft === "Small Text") return "Small Text";
		if (
			[
				"Link",
				"Dynamic Link",
				"Select",
				"Date",
				"Datetime",
				"Time",
				"Data",
				"Float",
				"Int",
				"Currency",
				"Percent",
				"Check",
			].includes(ft)
		) {
			return ft;
		}
		return "Data";
	}

	function open_field_edit_dialog(frm, fieldname) {
		if (!can_edit_dashboard(frm)) {
			frappe.show_alert({ message: __("This Change Request is not editable."), indicator: "orange" });
			return;
		}
		const df = frappe.meta.get_docfield("Change Request", fieldname);
		if (!df) {
			frappe.msgprint(__("Unknown field: {0}", [fieldname]));
			return;
		}
		const baseline = parse_baseline(frm);
		const original = ((baseline && baseline.header) || {})[fieldname];
		const current = frm.doc[fieldname];
		const label = field_label(fieldname);
		const ft = dialog_fieldtype(df);

		const fields = [
			{
				fieldtype: "HTML",
				fieldname: "original_html",
				options:
					'<div class="cr-dash__dialog-original"><span class="text-muted">' +
					esc(__("Original (From Job)")) +
					"</span><div>" +
					val_box("old", normalize_for_compare(fieldname, original)) +
					"</div></div>",
			},
			{
				label: __("Proposed Value"),
				fieldname: "proposed",
				fieldtype: ft,
				options: df.options,
				reqd: cint(df.reqd) || 0,
				default: current,
			},
		];

		const d = new frappe.ui.Dialog({
			title: __("Edit {0}", [label]),
			fields: fields,
			primary_action_label: __("Apply"),
			primary_action: function (values) {
				let next = values.proposed;
				if (ft === "Check") {
					next = cint(next);
				}
				d.hide();
				Promise.resolve(frm.set_value(fieldname, next)).then(function () {
					frm.dirty();
					render_dashboard(frm);
					frappe.show_alert({
						message: __("{0} updated", [label]),
						indicator: "green",
					});
				});
			},
		});
		d.set_secondary_action_label(__("Revert to Original"));
		d.set_secondary_action(function () {
			d.hide();
			revert_field(frm, fieldname, original);
		});
		d.show();
		if (d.fields_dict.proposed && d.fields_dict.proposed.set_value) {
			d.fields_dict.proposed.set_value(current);
		}
	}

	function revert_field(frm, fieldname, original) {
		if (!can_edit_dashboard(frm)) return;
		if (original === undefined) {
			const baseline = parse_baseline(frm);
			original = ((baseline && baseline.header) || {})[fieldname];
		}
		const label = field_label(fieldname);
		Promise.resolve(frm.set_value(fieldname, original == null ? null : original)).then(function () {
			frm.dirty();
			render_dashboard(frm);
			frappe.show_alert({
				message: __("{0} reverted to original", [label]),
				indicator: "blue",
			});
		});
	}

	function cell_diff(old_v, new_v, action) {
		if (action === "Add") {
			return val_box("new", new_v);
		}
		if (action === "Remove") {
			return val_box("old", old_v);
		}
		if (cstr(old_v) === cstr(new_v)) {
			return '<span class="cr-dash__plain">' + esc(display_val(new_v)) + "</span>";
		}
		return (
			'<span class="cr-dash__inline-diff">' +
			val_box("old", old_v) +
			'<span class="cr-dash__arrow-sm">→</span>' +
			val_box("new", new_v) +
			"</span>"
		);
	}

	function dims_diff(prev, row, action) {
		const fmt = function (r) {
			if (r.length == null && r.width == null && r.height == null) return "";
			return [r.length, r.width, r.height]
				.map(function (x) {
					return x == null || x === "" ? "—" : cstr(x);
				})
				.join("×");
		};
		return cell_diff(fmt(prev || {}), fmt(row || {}), action);
	}

	function render_packages_rows(frm) {
		const baseline = parse_baseline(frm);
		const pkgs = base_pkg_map(baseline);
		const rows = frm.doc.package_changes || [];
		if (!rows.length) {
			return (
				'<div class="cr-dash__empty">' +
				esc(__("No package row changes.")) +
				"</div>"
			);
		}
		let html =
			'<div class="cr-dash__table-wrap"><table class="cr-dash__table cr-dash__table--rows">' +
			"<thead><tr>" +
			"<th>#</th><th>" +
			esc(__("Action")) +
			"</th><th>" +
			esc(__("Commodity")) +
			"</th><th>" +
			esc(__("No. of Packs")) +
			"</th><th>" +
			esc(__("Qty")) +
			"</th><th>" +
			esc(__("UOM")) +
			"</th><th>" +
			esc(__("Weight (kg)")) +
			"</th><th>" +
			esc(__("Volume (m³)")) +
			"</th><th>" +
			esc(__("Dimensions")) +
			"</th></tr></thead><tbody>";

		rows.forEach(function (row, i) {
			const action = cstr(row.row_action || "Update").trim();
			const prev = pkgs[cstr(row.source_row_name)] || {};
			let action_cls = "cr-dash__action";
			if (action === "Add") action_cls += " is-add";
			if (action === "Remove") action_cls += " is-remove";
			if (action === "Update") action_cls += " is-update";
			html +=
				"<tr><td>" +
				(i + 1) +
				'</td><td><span class="' +
				action_cls +
				'">' +
				esc(__(action)) +
				"</span></td><td>" +
				cell_diff(prev.commodity, row.commodity, action) +
				"</td><td>" +
				cell_diff(prev.no_of_packs, row.no_of_packs, action) +
				"</td><td>" +
				cell_diff(prev.quantity, row.quantity, action) +
				"</td><td>" +
				cell_diff(prev.uom, row.uom, action) +
				"</td><td>" +
				cell_diff(prev.weight, row.weight, action) +
				"</td><td>" +
				cell_diff(prev.volume, row.volume, action) +
				"</td><td>" +
				dims_diff(prev, row, action) +
				"</td></tr>";
		});
		html += "</tbody></table></div>";
		return html;
	}

	function render_charges_rows(frm) {
		const rows = frm.doc.charges || [];
		if (!rows.length) {
			return '<div class="cr-dash__empty">' + esc(__("No charge rows.")) + "</div>";
		}
		let html =
			'<div class="cr-dash__table-wrap"><table class="cr-dash__table">' +
			"<thead><tr><th>#</th><th>" +
			esc(__("Item")) +
			"</th><th>" +
			esc(__("Service Type")) +
			"</th><th>" +
			esc(__("Qty")) +
			"</th><th>" +
			esc(__("Est. Revenue")) +
			"</th><th>" +
			esc(__("Est. Cost")) +
			"</th></tr></thead><tbody>";
		rows.forEach(function (row, i) {
			html +=
				"<tr><td>" +
				(i + 1) +
				"</td><td>" +
				esc(row.item_code || row.item_name || "—") +
				"</td><td>" +
				esc(row.service_type || "—") +
				"</td><td>" +
				esc(display_val(row.quantity)) +
				"</td><td>" +
				esc(display_val(row.estimated_revenue)) +
				"</td><td>" +
				esc(display_val(row.estimated_cost)) +
				"</td></tr>";
		});
		html += "</tbody></table></div>";
		return html;
	}

	function render_services_rows(frm) {
		const rows = frm.doc.linked_services || [];
		if (!rows.length) {
			return '<div class="cr-dash__empty">' + esc(__("No linked services.")) + "</div>";
		}
		let html =
			'<div class="cr-dash__table-wrap"><table class="cr-dash__table">' +
			"<thead><tr><th>#</th><th>" +
			esc(__("Service Type")) +
			"</th><th>" +
			esc(__("Job Type")) +
			"</th><th>" +
			esc(__("Job No")) +
			"</th><th>" +
			esc(__("Description")) +
			"</th></tr></thead><tbody>";
		rows.forEach(function (row, i) {
			html +=
				"<tr><td>" +
				(i + 1) +
				"</td><td>" +
				esc(row.service_type || "—") +
				"</td><td>" +
				esc(row.job_type || "—") +
				"</td><td>" +
				esc(row.job_no || "—") +
				"</td><td>" +
				esc(row.job_description || "—") +
				"</td></tr>";
		});
		html += "</tbody></table></div>";
		return html;
	}

	function render_row_changes(frm, active_sub) {
		const pkg_n = (frm.doc.package_changes || []).length;
		const chg_n = (frm.doc.charges || []).length;
		const svc_n = (frm.doc.linked_services || []).length;
		active_sub = active_sub || "packages";

		let body = "";
		if (active_sub === "charges") body = render_charges_rows(frm);
		else if (active_sub === "services") body = render_services_rows(frm);
		else body = render_packages_rows(frm);

		const edit_label =
			active_sub === "charges"
				? __("Edit Charges")
				: active_sub === "services"
					? __("Edit Services")
					: __("Edit Packages");
		const edit_action =
			active_sub === "charges"
				? "goto-charges"
				: active_sub === "services"
					? "goto-services"
					: "goto-packages";

		return (
			'<div class="cr-dash__card">' +
			'<div class="cr-dash__card-head">' +
			'<h4 class="cr-dash__card-title">' +
			esc(__("Row Changes")) +
			"</h4>" +
			'<div class="cr-dash__head-actions">' +
			'<button type="button" class="cr-dash__btn" data-cr-action="export-rows">' +
			esc(__("Export")) +
			"</button>" +
			'<button type="button" class="cr-dash__btn cr-dash__btn--primary" data-cr-action="' +
			edit_action +
			'">' +
			esc(edit_label) +
			"</button></div></div>" +
			'<div class="cr-dash__subtabs">' +
			'<button type="button" class="cr-dash__subtab' +
			(active_sub === "packages" ? " is-active" : "") +
			'" data-cr-subtab="packages">' +
			esc(__("Packages")) +
			" (" +
			pkg_n +
			")</button>" +
			'<button type="button" class="cr-dash__subtab' +
			(active_sub === "charges" ? " is-active" : "") +
			'" data-cr-subtab="charges">' +
			esc(__("Charges")) +
			" (" +
			chg_n +
			")</button>" +
			'<button type="button" class="cr-dash__subtab' +
			(active_sub === "services" ? " is-active" : "") +
			'" data-cr-subtab="services">' +
			esc(__("Linked Services")) +
			" (" +
			svc_n +
			")</button></div>" +
			body +
			'<div class="cr-dash__legend">' +
			'<span><i class="cr-dash__swatch cr-dash__swatch--old"></i> ' +
			esc(__("Original Value")) +
			"</span>" +
			'<span><i class="cr-dash__swatch cr-dash__swatch--new"></i> ' +
			esc(__("Proposed Value")) +
			"</span></div></div>"
		);
	}

	function build_dashboard_html(frm) {
		const counts = section_counts(frm);
		const reason = cstr(frm.doc.reason);
		const show_unchanged = !!frm._cr_dash_show_unchanged;
		const subtab = frm._cr_dash_subtab || "packages";

		return (
			'<div class="cr-dash">' +
			'<div class="cr-dash__card">' +
			'<div class="cr-dash__card-head">' +
			'<h4 class="cr-dash__card-title">' +
			esc(__("Change Summary")) +
			' <i class="fa fa-info-circle text-muted" title="' +
			esc(__("Counts of fields and rows that differ from the job baseline")) +
			'"></i></h4>' +
			'<button type="button" class="cr-dash__link" data-cr-action="full-comparison">' +
			esc(__("View Full Comparison")) +
			"</button></div>" +
			(reason
				? '<p class="cr-dash__reason"><span class="text-muted">' +
					esc(__("Reason")) +
					":</span> " +
					esc(reason) +
					"</p>"
				: "") +
			render_tiles(counts) +
			"</div>" +
			render_field_changes(frm, show_unchanged) +
			render_row_changes(frm, subtab) +
			"</div>"
		);
	}

	function set_html_field(frm, fieldname, html) {
		const field = frm.fields_dict && frm.fields_dict[fieldname];
		if (!field || !field.$wrapper) return null;
		field.$wrapper
			.closest(".form-section, .form-column")
			.removeClass("hide-control empty-section")
			.addClass("visible-section");
		field.$wrapper.removeClass("hide-control");
		if (typeof field.html === "function") {
			field.html(html);
		} else {
			let $box = field.$wrapper.find(".html-value").first();
			if (!$box.length) {
				$box = $('<div class="html-value"></div>');
				field.$wrapper.empty().append($box);
			}
			$box.html(html);
		}
		return field.$wrapper;
	}

	function set_active_tab(frm, tab_fieldname) {
		if (!frm.layout || !frm.layout.tabs) return;
		const tab = frm.layout.tabs.find(function (t) {
			return t.df && t.df.fieldname === tab_fieldname;
		});
		if (tab && tab.set_active) tab.set_active();
		else if (frm.set_active_tab) frm.set_active_tab(tab_fieldname);
	}

	function export_rows_csv(frm) {
		const sub = frm._cr_dash_subtab || "packages";
		let headers = [];
		let lines = [];
		if (sub === "charges") {
			headers = ["#", "Item", "Service Type", "Qty", "Est Revenue", "Est Cost"];
			(frm.doc.charges || []).forEach(function (r, i) {
				lines.push([i + 1, r.item_code || "", r.service_type || "", r.quantity || "", r.estimated_revenue || "", r.estimated_cost || ""]);
			});
		} else if (sub === "services") {
			headers = ["#", "Service Type", "Job Type", "Job No", "Description"];
			(frm.doc.linked_services || []).forEach(function (r, i) {
				lines.push([i + 1, r.service_type || "", r.job_type || "", r.job_no || "", r.job_description || ""]);
			});
		} else {
			headers = ["#", "Action", "Commodity", "No of Packs", "Qty", "UOM", "Weight", "Volume"];
			(frm.doc.package_changes || []).forEach(function (r, i) {
				lines.push([
					i + 1,
					r.row_action || "",
					r.commodity || "",
					r.no_of_packs || "",
					r.quantity || "",
					r.uom || "",
					r.weight || "",
					r.volume || "",
				]);
			});
		}
		const csv = [headers]
			.concat(lines)
			.map(function (row) {
				return row
					.map(function (c) {
						const s = cstr(c).replace(/"/g, '""');
						return '"' + s + '"';
					})
					.join(",");
			})
			.join("\n");
		const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = (frm.doc.name || "change-request") + "-" + sub + ".csv";
		a.click();
		URL.revokeObjectURL(url);
	}

	function show_full_comparison(frm) {
		const diffs = collect_field_diffs(frm);
		const list = diffs.changed.length ? diffs.changed : [];
		const groups = group_rows_by_job_layout(list, diffs.layout);

		let body = "";
		if (!groups.length) {
			body =
				'<div class="cr-dash__empty">' +
				esc(__("No differences from baseline yet.")) +
				"</div>";
		} else {
			let last_tab = null;
			groups.forEach(function (g) {
				if (g.tab !== last_tab) {
					body +=
						'<h5 class="cr-dash__tab-title">' +
						esc(__(g.tab)) +
						"</h5>";
					last_tab = g.tab;
				}
				if (g.form_section) {
					body +=
						'<h6 class="cr-dash__section-title">' +
						esc(__(g.form_section)) +
						"</h6>";
				}
				body +=
					'<div class="cr-dash__table-wrap" style="margin-bottom:12px"><table class="cr-dash__table"><thead><tr>' +
					"<th>" +
					esc(__("Field")) +
					"</th><th>" +
					esc(__("Original")) +
					"</th><th>" +
					esc(__("Proposed")) +
					"</th></tr></thead><tbody>";
				g.rows.forEach(function (r) {
					body +=
						"<tr><td>" +
						esc(r.label) +
						"</td><td>" +
						val_box("old", r.from) +
						"</td><td>" +
						val_box("new", r.to) +
						"</td></tr>";
				});
				body += "</tbody></table></div>";
			});
		}
		const d = new frappe.ui.Dialog({
			title: __("Full Comparison"),
			size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "cmp" }],
		});
		d.fields_dict.cmp.$wrapper.html('<div class="cr-dash">' + body + "</div>");
		d.show();
	}

	function bind_actions(frm, $root) {
		if (!$root || !$root.length) return;
		$root.off("click.crDash");
		$root.on("click.crDash", "[data-cr-section]", function () {
			const section = $(this).attr("data-cr-section");
			const tab = SECTION_TABS[section];
			if (tab) set_active_tab(frm, tab);
		});
		$root.on("click.crDash", "[data-cr-subtab]", function () {
			frm._cr_dash_subtab = $(this).attr("data-cr-subtab");
			render_dashboard(frm);
		});
		$root.on("click.crDash", "[data-cr-edit-field]", function (e) {
			e.preventDefault();
			e.stopPropagation();
			open_field_edit_dialog(frm, $(this).attr("data-cr-edit-field"));
		});
		$root.on("click.crDash", "[data-cr-revert-field]", function (e) {
			e.preventDefault();
			e.stopPropagation();
			revert_field(frm, $(this).attr("data-cr-revert-field"));
		});
		$root.on("click.crDash", "[data-cr-action]", function () {
			const action = $(this).attr("data-cr-action");
			if (action === "toggle-unchanged") {
				frm._cr_dash_show_unchanged = !frm._cr_dash_show_unchanged;
				render_dashboard(frm);
				return;
			}
			if (action === "full-comparison") {
				show_full_comparison(frm);
				return;
			}
			if (action === "export-rows") {
				export_rows_csv(frm);
				return;
			}
			if (action === "goto-packages") {
				set_active_tab(frm, "packages_tab");
				return;
			}
			if (action === "goto-charges") {
				set_active_tab(frm, "charges_tab");
				return;
			}
			if (action === "goto-services") {
				set_active_tab(frm, "services_tab");
			}
		});
	}

	function render_approvals(frm) {
		const status = cstr(frm.doc.status || "Draft");
		const sections = cstr(frm.doc.change_sections)
			.replace(/,/g, "\n")
			.split("\n")
			.map(function (s) {
				return s.trim();
			})
			.filter(Boolean);
		let html =
			'<div class="cr-dash__card"><h4 class="cr-dash__card-title">' +
			esc(__("Approvals")) +
			"</h4>" +
			'<div class="cr-dash__kv"><span class="text-muted">' +
			esc(__("Status")) +
			'</span><span>' +
			esc(__(status)) +
			"</span></div>" +
			'<div class="cr-dash__kv"><span class="text-muted">' +
			esc(__("Requested By")) +
			"</span><span>" +
			esc(frm.doc.owner || "—") +
			"</span></div>" +
			'<div class="cr-dash__kv"><span class="text-muted">' +
			esc(__("Change Sections")) +
			'</span><span class="cr-dash__tags">';
		(sections.length ? sections : ["—"]).forEach(function (s) {
			html += '<span class="cr-dash__tag">' + esc(__(s)) + "</span>";
		});
		html += "</span></div></div>";
		return html;
	}

	function render_history(frm, versions) {
		let html =
			'<div class="cr-dash__card"><h4 class="cr-dash__card-title">' +
			esc(__("History")) +
			"</h4>";
		if (!versions || !versions.length) {
			html +=
				'<div class="cr-dash__empty">' +
				esc(__("No history yet.")) +
				"</div></div>";
			return html;
		}
		html += '<ul class="cr-dash__history">';
		versions.forEach(function (v) {
			html +=
				"<li><span class=\"text-muted\">" +
				esc(frappe.datetime.str_to_user(v.creation) || v.creation) +
				"</span> <strong>" +
				esc(v.owner || "") +
				"</strong></li>";
		});
		html += "</ul></div>";
		return html;
	}

	function load_history(frm) {
		if (!frm.fields_dict.history_html) return;
		if (frm.is_new()) {
			set_html_field(frm, "history_html", render_history(frm, []));
			return;
		}
		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "Version",
				filters: { ref_doctype: "Change Request", docname: frm.doc.name },
				fields: ["name", "owner", "creation"],
				order_by: "creation desc",
				limit_page_length: 30,
			},
			callback: function (r) {
				set_html_field(frm, "history_html", render_history(frm, r.message || []));
			},
		});
	}

	function render_dashboard(frm) {
		function paint() {
			const $root = set_html_field(frm, "dashboard_html", build_dashboard_html(frm));
			bind_actions(frm, $root);
			if (frm.fields_dict.approvals_html) {
				set_html_field(frm, "approvals_html", render_approvals(frm));
			}
			load_history(frm);
		}
		const job_type = cstr(frm.doc.job_type).trim();
		if (job_type && !build_job_field_layout(job_type)) {
			ensure_job_layout(frm, function () {
				paint();
			});
			// Show skeleton immediately while meta loads
			paint();
			return;
		}
		paint();
	}

	logistics.change_request_summary.render = render_dashboard;
	logistics.change_request_summary.section_counts = section_counts;
})();
