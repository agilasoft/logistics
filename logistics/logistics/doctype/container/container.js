// Copyright (c) 2025, Logistics Team and contributors
// For license information, please see license.txt

function _schedule_container_number_iso_check(frm) {
	if (frm._container_iso_timer) {
		clearTimeout(frm._container_iso_timer);
	}
	frm._container_iso_timer = setTimeout(() => {
		_run_container_number_iso_check(frm);
	}, 400);
}

function _run_container_number_iso_check(frm) {
	const raw = frm.doc.container_number;
	if (raw === undefined || raw === null || String(raw).trim() === "") {
		if (frm.fields_dict && frm.fields_dict.container_number) {
			frm.set_df_property("container_number", "description", "");
		}
		return;
	}
	frappe.call({
		method: "logistics.logistics.doctype.container.container.validate_container_number_for_form",
		args: { container_number: String(raw) },
		callback(r) {
			if (!frm.fields_dict || !frm.fields_dict.container_number) {
				return;
			}
			if (r.exc) {
				frm.set_df_property("container_number", "description", "");
				return;
			}
			const d = r.message || {};
			if (d.valid) {
				frm.set_df_property("container_number", "description", "");
			} else {
				const msg = frappe.utils.escape_html(d.message || __("Invalid container number"));
				frm.set_df_property(
					"container_number",
					"description",
					`<span class="text-danger">${msg}</span>`
				);
			}
		},
	});
}

frappe.ui.form.on("Container", {
	container_number(frm) {
		_schedule_container_number_iso_check(frm);
	},
	async validate(frm) {
		const raw = frm.doc.container_number;
		if (raw === undefined || raw === null || String(raw).trim() === "") {
			return;
		}
		try {
			const r = await frappe.call({
				method: "logistics.logistics.doctype.container.container.validate_container_number_for_form",
				args: { container_number: String(raw) },
			});
			const d = r.message || {};
			if (!d.valid) {
				frappe.validated = false;
				frappe.msgprint({
					title: __("Invalid Container Number"),
					message: d.message || __("Invalid container number"),
					indicator: "red",
				});
			}
		} catch (e) {
			// Network / server error: server-side validate still runs on save
		}
	},
	is_active(frm) {
		if (frm.doc.is_active) {
			frm.set_value("assignment_inactive_reason", null);
		}
	},
	refresh: function (frm) {
		_schedule_container_number_iso_check(frm);
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
			frm.add_custom_button(
				__("Request CD Refund"),
				function () {
					if (!_container_eligible_for_cd_refund_request(frm)) {
						frappe.msgprint(
							__(
								"Container must be returned (Empty Returned / Closed or Return status Returned) before requesting CD refund."
							)
						);
						return;
					}
					_prompt_cd_refund_deposit_row(frm, __("Request CD Refund (Dr AR / Cr pending refund)"), function (row_name) {
						frappe.call({
							method:
								"logistics.logistics.deposit_processing.container_deposit_gl.create_request_cd_refund_journal_entry",
							args: { container_name: frm.doc.name, child_row_name: row_name },
							callback: function (r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.show_alert({ message: __("Journal Entry {0}", [r.message]), indicator: "green" });
								}
							},
						});
					});
				},
				__("Container deposit")
			);
		}
		if (frm.doc.__islocal || !frm.doc.name) return;
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_shipments_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_shipments) {
					frm.fields_dict.linked_shipments.$wrapper.html(r.message);
				}
			},
		});
		frappe.call({
			method: "logistics.logistics.doctype.container.container.get_linked_transport_jobs_html",
			args: { container: frm.doc.name },
			callback: function (r) {
				if (r.message && frm.fields_dict.linked_transport_jobs) {
					frm.fields_dict.linked_transport_jobs.$wrapper.html(r.message);
				}
			},
		});
	},
});

function _container_eligible_for_cd_refund_request(frm) {
	const rs = frm.doc.return_status || "";
	const st = frm.doc.status || "";
	if (rs === "Returned") {
		return true;
	}
	if (st === "Empty Returned" || st === "Closed") {
		return true;
	}
	return false;
}

function _prompt_cd_refund_deposit_row(frm, title, callback) {
	const rows = (frm.doc.deposits || []).filter(
		(r) =>
			r.name &&
			r.purchase_invoice &&
			!r.refund_request_journal_entry &&
			frappe.utils.flt(r.deposit_amount) > 0
	);
	if (!rows.length) {
		frappe.msgprint(
			__(
				"No eligible deposit lines: need a line linked to a Purchase Invoice, positive amount, and no refund request JE yet."
			)
		);
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
