// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

frappe.ui.form.on("Container", {
	is_active(frm) {
		if (frm.doc.is_active) {
			frm.set_value("assignment_inactive_reason", null);
		}
	},
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Refresh refund checklist"), function () {
				frappe.call({
					method: "logistics.logistics.deposit_processing.container_deposit_gl.materialize_refund_readiness",
					args: { container_name: frm.doc.name },
					callback: function (r) {
						if (!r.exc) {
							frm.reload_doc();
							frappe.show_alert({ message: __("Refund checklist updated"), indicator: "green" });
						}
					},
				});
			});
			frm.add_custom_button(__("Pending carrier pay JE"), function () {
				_prompt_deposit_row(frm, __("Post pending carrier pay (AR)"), function (row_name) {
					frappe.call({
						method: "logistics.logistics.deposit_processing.container_deposit_gl.create_pending_carrier_pay_je",
						args: { container_name: frm.doc.name, child_row_name: row_name },
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
								frappe.show_alert({ message: __("Journal Entry {0}", [r.message]), indicator: "green" });
							}
						},
					});
				});
			}, __("Container deposit"));
			frm.add_custom_button(__("Pending carrier refund JE"), function () {
				_prompt_deposit_row(frm, __("Post pending refund from carrier (AR)"), function (row_name) {
					frappe.call({
						method: "logistics.logistics.deposit_processing.container_deposit_gl.create_pending_refund_from_carrier_je",
						args: { container_name: frm.doc.name, child_row_name: row_name },
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
								frappe.show_alert({ message: __("Journal Entry {0}", [r.message]), indicator: "green" });
							}
						},
					});
				});
			}, __("Container deposit"));
			frm.add_custom_button(__("Bank pay carrier JE"), function () {
				_prompt_deposit_row(frm, __("Settle bank payment to carrier"), function (row_name) {
					frappe.call({
						method: "logistics.logistics.deposit_processing.container_deposit_gl.create_bank_settle_carrier_pay_je",
						args: { container_name: frm.doc.name, child_row_name: row_name },
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
								frappe.show_alert({ message: __("Journal Entry {0}", [r.message]), indicator: "green" });
							}
						},
					});
				});
			}, __("Container deposit"));
			frm.add_custom_button(__("Bank receive carrier refund JE"), function () {
				_prompt_deposit_row(frm, __("Bank receipt from carrier"), function (row_name) {
					frappe.call({
						method: "logistics.logistics.deposit_processing.container_deposit_gl.create_bank_receive_carrier_refund_je",
						args: { container_name: frm.doc.name, child_row_name: row_name },
						callback: function (r) {
							if (!r.exc) {
								frm.reload_doc();
								frappe.show_alert({ message: __("Journal Entry {0}", [r.message]), indicator: "green" });
							}
						},
					});
				});
			}, __("Container deposit"));
		}
		// Skip for new/unsaved docs - name is temporary and doc doesn't exist in DB
		if (frm.doc.__islocal || !frm.doc.name) return;
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_shipments_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_shipments) {
					frm.fields_dict.linked_shipments.$wrapper.html(r.message);
				}
			}
		});
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_transport_jobs_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_transport_jobs) {
					frm.fields_dict.linked_transport_jobs.$wrapper.html(r.message);
				}
			}
		});
	},
});

function _prompt_deposit_row(frm, title, callback) {
	const rows = (frm.doc.deposits || []).filter((r) => r.name);
	if (!rows.length) {
		frappe.msgprint(__("Add at least one deposit line with an amount."));
		return;
	}
	const d = new frappe.ui.Dialog({
		title: title,
		fields: [
			{
				fieldname: "row",
				fieldtype: "Select",
				label: __("Deposit row"),
				options: rows.map((r) => r.name).join("\n"),
				reqd: 1,
			},
		],
		primary_action_label: __("Post"),
		primary_action(values) {
			callback(values.row);
			d.hide();
		},
	});
	d.show();
}
