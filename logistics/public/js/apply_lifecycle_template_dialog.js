// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Shared "Apply Lifecycle Template" dialog used on both Special Project and Exhibit forms.
// The form-level button on each parent calls logistics_open_apply_lifecycle_template_dialog(frm, parentDoctype).
(function () {
	"use strict";

	function _applicability_filter(parent_doctype) {
		if (parent_doctype === "Special Project") {
			return { enabled: 1, for_special_project: 1 };
		}
		if (parent_doctype === "Exhibit") {
			return { enabled: 1, for_exhibits: 1 };
		}
		return { enabled: 1 };
	}

	window.logistics_open_apply_lifecycle_template_dialog = function (frm, parent_doctype) {
		if (!frm || !frm.doc || !frm.doc.name) {
			frappe.msgprint(__("Save the document first."));
			return;
		}
		const filters = _applicability_filter(parent_doctype);

		const d = new frappe.ui.Dialog({
			title: __("Apply Lifecycle Template"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "template",
					label: __("Lifecycle Template"),
					options: "Lifecycle Template",
					reqd: 1,
					get_query: function () {
						return { filters: filters };
					},
				},
				{
					fieldtype: "HTML",
					fieldname: "template_preview",
					options: "<div class='text-muted small'>" +
						__("Pick a template to preview its activities.") +
						"</div>",
				},
				{
					fieldtype: "Section Break",
					label: __("Options"),
				},
				{
					fieldtype: "Check",
					fieldname: "replace_existing",
					label: __("Replace existing lifecycle rows (without job)"),
					description: __(
						"When ticked, existing Lifecycle rows that have NOT yet generated a booking/order are removed before appending. Rows already linked to a booking/order are always kept."
					),
				},
			],
			primary_action_label: __("Apply"),
			primary_action: function (values) {
				if (!values.template) {
					frappe.msgprint(__("Pick a Lifecycle Template."));
					return;
				}
				frappe.call({
					method: "logistics.utils.lifecycle_template.apply_lifecycle_template",
					args: {
						parent_doctype: parent_doctype,
						parent_name: frm.doc.name,
						template: values.template,
						replace_existing: values.replace_existing ? 1 : 0,
					},
					freeze: true,
					freeze_message: __("Applying template..."),
					callback: function (r) {
						d.hide();
						if (r && r.message) {
							const m = r.message;
							const parts = [];
							if (m.added) parts.push(__("{0} added", [m.added]));
							if (m.removed) parts.push(__("{0} removed", [m.removed]));
							if (m.kept) parts.push(__("{0} kept (linked)", [m.kept]));
							if (m.skipped) parts.push(__("{0} skipped", [m.skipped]));
							if (parts.length) {
								frappe.show_alert(
									{ message: parts.join(" \u00b7 "), indicator: "green" },
									7
								);
							}
						}
						frm.reload_doc();
					},
				});
			},
		});

		d.fields_dict.template.df.onchange = function () {
			const tpl = d.get_value("template");
			const $area = d.fields_dict.template_preview.$wrapper;
			if (!tpl) {
				$area.html(
					"<div class='text-muted small'>" +
						__("Pick a template to preview its activities.") +
						"</div>"
				);
				return;
			}
			$area.html(
				"<div class='text-muted small'>" + __("Loading...") + "</div>"
			);
			frappe.db.get_doc("Lifecycle Template", tpl).then(function (doc) {
				const acts = (doc.activities || [])
					.slice()
					.sort(function (a, b) {
						return (a.sort_order || 0) - (b.sort_order || 0);
					});
				if (!acts.length) {
					$area.html(
						"<div class='text-muted small'>" +
							__("This template has no activity rows.") +
							"</div>"
					);
					return;
				}
				const rows = acts
					.map(function (a) {
						const name = frappe.utils.escape_html(a.activity_name || a.activity_code || "-");
						const stage = frappe.utils.escape_html(a.lifecycle_stage || "-");
						const service = frappe.utils.escape_html(a.service_type || "-");
						return (
							"<tr><td>" + stage + "</td><td>" + name + "</td><td>" + service + "</td></tr>"
						);
					})
					.join("");
				$area.html(
					"<div class='small text-muted' style='margin-bottom:6px'>" +
						__("{0} activity row(s) will be appended", [acts.length]) +
						"</div>" +
						"<table class='table table-bordered table-sm' style='margin:0;background:#fff'>" +
						"<thead><tr><th>" + __("Stage") + "</th><th>" + __("Activity") +
						"</th><th>" + __("Service") + "</th></tr></thead><tbody>" +
						rows +
						"</tbody></table>"
				);
			});
		};

		d.show();
	};
})();
