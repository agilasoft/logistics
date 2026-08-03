// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Time Sensitive Case form:
 * - Toolbar [Services] opens Manage Linked Services dialog (add / remove).
 * - Services tab grid is a read-only live view.
 */

function logistics_ts_setup_read_only_linked_services_grid(frm) {
	if (window.logistics && logistics.setup_virtual_linked_services_grid) {
		logistics.setup_virtual_linked_services_grid(frm);
		return;
	}
	if (!frm.get_docfield || !frm.get_docfield("linked_services")) return;
	frm.set_df_property("linked_services", "read_only", 1);
	frm.set_df_property("linked_services", "cannot_add_rows", 1);
	frm.set_df_property("linked_services", "cannot_delete_rows", 1);
}

function logistics_ts_open_services_dialog(frm) {
	function open() {
		if (logistics.time_sensitive && logistics.time_sensitive.show_services_dialog) {
			logistics.time_sensitive.show_services_dialog(frm);
			return;
		}
		frappe.msgprint({
			message: __("Services dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."),
			indicator: "orange",
		});
	}
	if (logistics.time_sensitive && logistics.time_sensitive.show_services_dialog) {
		open();
		return;
	}
	frappe.require("/assets/logistics/js/time_sensitive_services_dialog.js", open);
}

function logistics_ts_setup_services_button(frm) {
	if (frm.is_new()) return;
	frm.add_custom_button(__("Services"), () => {
		logistics_ts_open_services_dialog(frm);
	});
}

function logistics_ts_open_fetch_from_quote_dialog(frm) {
	function open() {
		if (!logistics.show_ts_sq_fetch_dialog) {
			frappe.msgprint({
				message: __("Fetch dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."),
				indicator: "orange",
			});
			return;
		}
		logistics.show_ts_sq_fetch_dialog(frm, { direction: "quote_to_case" });
	}
	if (logistics.show_ts_sq_fetch_dialog) {
		open();
		return;
	}
	frappe.require("/assets/logistics/js/ts_sq_fetch_dialog.js", open);
}

function logistics_ts_setup_fetch_button(frm) {
	if (frm.is_new() || !frm.doc.sales_quote) return;
	frm.add_custom_button(__("Fetch from Sales Quote"), () => {
		logistics_ts_open_fetch_from_quote_dialog(frm);
	}, __("Get Items"));
}

function logistics_ts_setup_actions_menu(frm) {
	if (frm.is_new()) return;

	if (!frm.doc.acknowledged_on && ["Activated", "In Execution", "Triage"].includes(frm.doc.status)) {
		frm.add_custom_button(__("Acknowledge"), () => {
			frappe.call({
				method: "logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.acknowledge_case",
				args: { name: frm.doc.name },
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
		}).addClass("btn-primary");
	}

	if (["Draft", "Triage"].includes(frm.doc.status)) {
		frm.add_custom_button(
			__("Activate"),
			() => {
				frappe.call({
					method: "logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.activate_case",
					args: { name: frm.doc.name },
					freeze: true,
					callback() {
						frm.reload_doc();
					},
				});
			},
			__("Actions")
		);
	}

	frm.add_custom_button(
		__("Log Exception"),
		() => {
			frappe.prompt(
				[{ fieldname: "message", fieldtype: "Small Text", label: __("Exception"), reqd: 1 }],
				(v) => {
					frappe.call({
						method: "logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.log_case_event",
						args: {
							name: frm.doc.name,
							event_type: "Exception",
							message: v.message,
							severity: "critical",
						},
						freeze: true,
						callback() {
							frm.reload_doc();
						},
					});
				},
				__("Log Exception")
			);
		},
		__("Actions")
	);

	frm.add_custom_button(
		__("Attach Document"),
		() => {
			frappe.prompt(
				[
					{
						fieldname: "doctype",
						fieldtype: "Link",
						options: "DocType",
						label: __("DocType"),
						reqd: 1,
					},
					{
						fieldname: "docname",
						fieldtype: "Dynamic Link",
						options: "doctype",
						label: __("Document"),
						reqd: 1,
					},
				],
				(v) => {
					frappe.call({
						method:
							"logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.attach_operational_document",
						args: {
							case_name: frm.doc.name,
							doctype: v.doctype,
							docname: v.docname,
						},
						freeze: true,
						callback() {
							frm.reload_doc();
						},
					});
				},
				__("Attach Operational Document")
			);
		},
		__("Actions")
	);
}

function logistics_ts_setup_create_service_buttons(frm) {
	(frm.doc.linked_services || []).forEach((service) => {
		if (!service.job_no && service.linked_service) {
			frm.add_custom_button(
				__("Create {0}: {1}", [service.service_type, service.linked_service]),
				() => {
					frappe.call({
						method:
							"logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.create_service_document",
						args: {
							case_name: frm.doc.name,
							linked_service: service.linked_service,
						},
						freeze: true,
						callback(r) {
							frm.reload_doc();
							if (r.message) {
								frappe.set_route("Form", r.message.doctype, r.message.name);
							}
						},
					});
				},
				__("Create Service")
			);
		}
	});
}

frappe.ui.form.on("Time Sensitive Case", {
	refresh(frm) {
		logistics_ts_setup_read_only_linked_services_grid(frm);
		frm._ts_timer_stop && frm._ts_timer_stop();
		if (frm.doc.critical_deadline) {
			logistics.time_sensitive.timer.setFormIndicator(
				frm,
				frm.doc.critical_deadline,
				frm.doc.at_risk_hours || 4
			);
			if (frm.fields_dict.ts_countdown) {
				frm._ts_timer_stop = logistics.time_sensitive.timer.mountTimer({
					$wrapper: $(frm.fields_dict.ts_countdown.wrapper),
					deadline: frm.doc.critical_deadline,
					atRiskHours: frm.doc.at_risk_hours || 4,
					label: __("Critical"),
				});
			}
		}

		logistics_ts_setup_services_button(frm);
		logistics_ts_setup_fetch_button(frm);
		logistics_ts_setup_actions_menu(frm);
		logistics_ts_setup_create_service_buttons(frm);
	},

	case_type(frm) {
		if (!frm.doc.case_type) return;
		frappe.db.get_doc("Time Sensitive Case Type", frm.doc.case_type).then((ct) => {
			if (ct.default_severity) frm.set_value("severity", ct.default_severity);
			if (ct.default_at_risk_hours) frm.set_value("at_risk_hours", ct.default_at_risk_hours);
			if (ct.milestone_template) frm.set_value("milestone_template", ct.milestone_template);
			if (ct.document_list_template)
				frm.set_value("document_list_template", ct.document_list_template);
		});
	},

	critical_deadline(frm) {
		frm.refresh();
	},
});
