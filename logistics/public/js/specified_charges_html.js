// Copyright (c) 2026, www.agilasoft.com and contributors
// Specified Charges / Charge Group selection on charge grid rows (HTML + JSON; istable-safe).

frappe.provide("logistics.specified_charges");

(function () {
	"use strict";

	var CHARGE_DT =
		window.LOGISTICS_CHARGE_DOCTYPES_WITH_BREAKS ||
		[
			"Sea Booking Charges",
			"Sea Shipment Charges",
			"Sea Consolidation Charges",
			"Air Booking Charges",
			"Air Shipment Charges",
			"Declaration Charges",
			"Declaration Order Charges",
			"Transport Order Charges",
			"Transport Job Charges",
			"Special Project Charges",
			"Sales Quote Charge",
			"Tariff Charge",
			"MICE Project Charges",
			"MICE Project Consolidation Charges",
			"Exhibit Charges",
			"Time Sensitive Case Charge",
			"Change Request Charge",
		];

	var SPECS = [
		{
			json: "selling_specified_item_codes",
			html: "selling_specified_items_html",
			link_doctype: "Item",
			methods: ["Specified Charges"],
			method_fields: ["revenue_calculation_method", "calculation_method"],
		},
		{
			json: "selling_specified_charge_group_codes",
			html: "selling_specified_charge_groups_html",
			link_doctype: "Logistics Charge Group",
			methods: ["Based on Specified Charge Group"],
			method_fields: ["revenue_calculation_method", "calculation_method"],
		},
		{
			json: "cost_specified_item_codes",
			html: "cost_specified_items_html",
			link_doctype: "Item",
			methods: ["Specified Charges"],
			method_fields: ["cost_calculation_method"],
		},
		{
			json: "cost_specified_charge_group_codes",
			html: "cost_specified_charge_groups_html",
			link_doctype: "Logistics Charge Group",
			methods: ["Based on Specified Charge Group"],
			method_fields: ["cost_calculation_method"],
		},
	];

	var HTML_FIELDNAMES = SPECS.map(function (s) {
		return s.html;
	});

	function parse_codes(raw) {
		if (!raw) {
			return [];
		}
		if (Array.isArray(raw)) {
			return raw.filter(Boolean);
		}
		try {
			var parsed = JSON.parse(raw);
			return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
		} catch (e) {
			return String(raw)
				.split(",")
				.map(function (s) {
					return s.trim();
				})
				.filter(Boolean);
		}
	}

	function row_method_matches(row, spec) {
		for (var i = 0; i < spec.method_fields.length; i++) {
			var fn = spec.method_fields[i];
			var val = row[fn];
			if (val && spec.methods.indexOf(val) !== -1) {
				return true;
			}
		}
		return false;
	}

	function open_grid_row() {
		return frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
	}

	function grid_form_for_row(row) {
		var grid_row = open_grid_row();
		if (!grid_row || !grid_row.doc || grid_row.doc.name !== row.name) {
			return null;
		}
		return grid_row.grid_form || null;
	}

	function refresh_specified_html_fields(frm, cdt, cdn) {
		var grid_row = open_grid_row();
		if (!grid_row || !grid_row.grid_form) {
			return;
		}
		HTML_FIELDNAMES.forEach(function (fn) {
			if (grid_row.refresh_field) {
				grid_row.refresh_field(fn);
			}
		});
		if (grid_row.grid_form.layout && grid_row.grid_form.layout.refresh) {
			grid_row.grid_form.layout.refresh();
		}
	}

	function mount_wrapper(grid_form, spec, row) {
		var html_field = grid_form.fields_dict[spec.html];
		if (html_field && html_field.$wrapper) {
			return html_field.$wrapper;
		}
		var anchor =
			grid_form.fields_dict.revenue_calculation_method ||
			grid_form.fields_dict.calculation_method ||
			grid_form.fields_dict.cost_calculation_method;
		if (!anchor || !anchor.$wrapper) {
			return null;
		}
		var key = "logistics-spec-fb-" + spec.json;
		var $fb = anchor.$wrapper.parent().find("." + key);
		if (!$fb.length) {
			$fb = $('<div class="' + key + ' logistics-specified-charges-fallback"></div>').insertAfter(
				anchor.$wrapper
			);
		}
		return $fb;
	}

	function set_codes(frm, cdt, cdn, json_field, codes) {
		var json = JSON.stringify(codes || []);
		return frappe.model.set_value(cdt, cdn, json_field, json).then(function () {
			if (
				logistics.charge_type_cleanup &&
				logistics.charge_type_cleanup.recalculate_charge_row
			) {
				logistics.charge_type_cleanup.recalculate_charge_row(frm, cdt, cdn);
			}
		});
	}

	function render_specified_picker(frm, cdt, cdn, spec) {
		var row = locals[cdt] && locals[cdt][cdn] ? locals[cdt][cdn] : frappe.get_doc(cdt, cdn);
		if (!row) {
			return;
		}

		var grid_form = grid_form_for_row(row);
		if (!grid_form) {
			return;
		}

		var $w = mount_wrapper(grid_form, spec, row);
		if (!$w) {
			return;
		}

		var active = row_method_matches(row, spec);
		if (!active) {
			$w.hide().empty().removeData("logistics-spec-bound");
			return;
		}
		$w.show();

		if ($w.data("logistics-spec-bound") === spec.json) {
			logistics.specified_charges.refresh_picker($w, frm, cdt, cdn, spec);
			return;
		}
		$w.data("logistics-spec-bound", spec.json);
		$w.empty();

		var label =
			(spec.html.indexOf("group") !== -1 ? __("Specified Charge Groups") : __("Specified Items"));
		var $root = $('<div class="logistics-specified-charges-ui"></div>').appendTo($w);
		$('<label class="control-label">' + frappe.utils.escape_html(label) + "</label>").appendTo($root);
		var $pills = $('<div class="logistics-specified-pills mb-1 mt-1"></div>').appendTo($root);
		var $input_wrap = $('<div class="logistics-specified-link"></div>').appendTo($root);

		var link_df = {
			fieldtype: "Link",
			options: spec.link_doctype,
			fieldname: spec.json + "_link",
			label: spec.link_doctype === "Item" ? __("Add Item") : __("Add Charge Group"),
		};

		var link_control = frappe.ui.form.make_control({
			df: link_df,
			parent: $input_wrap,
			render_input: true,
			doc: row,
			frm: frm,
			parenttype: cdt,
			doctype: cdt,
			docname: cdn,
		});
		link_control.make();
		link_control.refresh();

		link_control.$input.on("awesomplete-selectcomplete", function () {
			var val = link_control.get_value();
			if (!val) {
				return;
			}
			var codes = parse_codes(frappe.get_doc(cdt, cdn)[spec.json]);
			if (codes.indexOf(val) !== -1) {
				link_control.set_value("");
				return;
			}
			codes.push(val);
			set_codes(frm, cdt, cdn, spec.json, codes).then(function () {
				link_control.set_value("");
				logistics.specified_charges.refresh_picker($w, frm, cdt, cdn, spec);
			});
		});

		$w.data("logistics-link-control", link_control);
		logistics.specified_charges.refresh_picker($w, frm, cdt, cdn, spec);
	}

	logistics.specified_charges.refresh_picker = function ($w, frm, cdt, cdn, spec) {
		var row = frappe.get_doc(cdt, cdn);
		var codes = parse_codes(row[spec.json]);
		var $pills = $w.find(".logistics-specified-pills");
		$pills.empty();

		codes.forEach(function (code) {
			var $pill = $(
				'<span class="data-pill btn btn-xs btn-default logistics-specified-pill mr-1 mb-1">' +
					frappe.utils.escape_html(code) +
					' <span class="logistics-spec-remove">&times;</span></span>'
			);
			$pill.find(".logistics-spec-remove").on("click", function (e) {
				e.preventDefault();
				e.stopPropagation();
				var next = codes.filter(function (c) {
					return c !== code;
				});
				set_codes(frm, cdt, cdn, spec.json, next).then(function () {
					logistics.specified_charges.refresh_picker($w, frm, cdt, cdn, spec);
				});
			});
			$pills.append($pill);
		});
	};

	logistics.specified_charges.render_all_for_row = function (frm, cdt, cdn) {
		refresh_specified_html_fields(frm, cdt, cdn);
		SPECS.forEach(function (spec) {
			render_specified_picker(frm, cdt, cdn, spec);
		});
	};

	function register_charge_doctype(doctype) {
		frappe.ui.form.on(doctype, {
			form_render: function (frm, cdt, cdn) {
				setTimeout(function () {
					logistics.specified_charges.render_all_for_row(frm, cdt, cdn);
				}, 80);
			},
		});

		SPECS.forEach(function (spec) {
			var handlers = {};
			handlers[spec.json] = function (frm, cdt, cdn) {
				if (
					logistics.charge_type_cleanup &&
					logistics.charge_type_cleanup.recalculate_charge_row
				) {
					logistics.charge_type_cleanup.recalculate_charge_row(frm, cdt, cdn);
				}
			};
			frappe.ui.form.on(doctype, handlers);
		});

		["revenue_calculation_method", "calculation_method", "cost_calculation_method"].forEach(function (fn) {
			frappe.ui.form.on(doctype, fn, function (frm, cdt, cdn) {
				setTimeout(function () {
					logistics.specified_charges.render_all_for_row(frm, cdt, cdn);
				}, 120);
			});
		});
	}

	CHARGE_DT.forEach(register_charge_doctype);

	["Air Freight Rate", "Sea Freight Rate", "Transport Rate", "Customs Rate", "Warehouse Rate"].forEach(
		register_charge_doctype
	);
})();
