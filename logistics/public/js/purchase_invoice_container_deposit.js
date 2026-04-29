// Copyright (c) 2026, Logistics Team and contributors
// Container-deposit Purchase Invoice lines: checkbox picker + Container link / accounting dimension sync.

(function () {
	"use strict";

	function show_container_deposit_dialog(frm, ctx) {
		const containers = ctx.containers || [];
		let html = '<div class="container-deposit-cb-list" style="max-height:280px;overflow:auto">';
		containers.forEach(function (c) {
			const val = frappe.utils.escape_html(c.value || "");
			const lbl = frappe.utils.escape_html(c.label || c.container_number || val);
			html +=
				'<div class="checkbox" style="margin-bottom:8px">' +
				"<label>" +
				'<input type="checkbox" class="pi-cd-cb" data-value="' +
				val +
				'" /> ' +
				lbl +
				"</label>" +
				"</div>";
		});
		html += "</div>";

		const d = new frappe.ui.Dialog({
			title: __("Containers for deposit lines"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "hint",
					options:
						"<p class='text-muted small'>" +
						__(
							"Each deposit line without a Container will be replaced by one row per selected container. Amount and quantity are split evenly across those rows; accounting dimensions update on save."
						) +
						"</p>",
				},
				{ fieldtype: "HTML", fieldname: "boxes", options: html },
			],
			primary_action_label: __("Apply"),
			primary_action() {
				const selected = [];
				d.$wrapper.find(".pi-cd-cb:checked").each(function () {
					selected.push($(this).attr("data-value"));
				});
				if (!selected.length) {
					frappe.msgprint(__("Select at least one container."));
					return;
				}
				frappe.call({
					method:
						"logistics.invoice_integration.container_deposit_pi_ui.apply_selected_containers_to_deposit_lines",
					args: {
						pi_name: frm.doc.name,
						container_names: selected,
					},
					freeze: true,
					callback(r) {
						if (!r.exc) {
							d.hide();
							frappe.show_alert({
								message: __("Container deposit lines updated"),
								indicator: "green",
							});
							frm.reload_doc();
						}
					},
				});
			},
		});
		d.show();
	}

	frappe.ui.form.on("Purchase Invoice", {
		refresh(frm) {
			if (frm.is_new() || frm.doc.docstatus !== 0) {
				return;
			}
			frm.add_custom_button(
				__("Allocate container deposits"),
				function () {
					frappe.call({
						method:
							"logistics.invoice_integration.container_deposit_pi_ui.get_container_deposit_checkbox_context",
						args: { pi_name: frm.doc.name },
						callback(r) {
							const ctx = r.message || {};
							if (!ctx.eligible) {
								frappe.msgprint({
									title: __("Container deposits"),
									message:
										ctx.reason ||
										__(
											"No container-deposit items or no containers on the linked job."
										),
									indicator: "orange",
								});
								return;
							}
							show_container_deposit_dialog(frm, ctx);
						},
					});
				},
				__("Tools")
			);
		},
	});
})();
