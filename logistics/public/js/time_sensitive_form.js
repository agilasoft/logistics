// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Shared form helpers for operational DocTypes flagged as time-sensitive.
 * Loaded via hooks doctype_js for bookings, shipments, orders, and jobs.
 */
frappe.provide("logistics.time_sensitive");

logistics.time_sensitive.setup_operational_form = function (frm) {
	if (!frm || !frm.fields_dict) return;

	const stopPrev = frm._ts_timer_stop;
	if (typeof stopPrev === "function") stopPrev();

	if (frm.doctype === "Sales Quote" && !frm.is_new()) {
		frm.add_custom_button(__("Create Time Sensitive Case"), () => {
			frappe.prompt(
				[
					{
						fieldname: "case_type",
						fieldtype: "Link",
						options: "Time Sensitive Case Type",
						label: __("Case Type"),
						reqd: 1,
						default: "AOG",
					},
					{
						fieldname: "critical_deadline",
						fieldtype: "Datetime",
						label: __("Critical Deadline"),
						default:
							frm.doc.critical_deadline ||
							frappe.datetime.add_to_date(frappe.datetime.now_datetime(), { hours: 24 }),
						reqd: 1,
					},
				],
				(values) => {
					frappe.call({
						method:
							"logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case.create_case_from_sales_quote",
						args: {
							sales_quote: frm.doc.name,
							case_type: values.case_type,
							critical_deadline: values.critical_deadline,
						},
						freeze: true,
						callback(r) {
							if (r.message && r.message.name) {
								frm.reload_doc();
								frappe.set_route("Form", "Time Sensitive Case", r.message.name);
							}
						},
					});
				},
				__("New Time Sensitive Case")
			);
		}, __("Time Sensitive"));
	}

	if (cint(frm.doc.is_time_sensitive) && frm.doc.critical_deadline) {
		logistics.time_sensitive.timer.setFormIndicator(frm, frm.doc.critical_deadline, 4);
		if (frm.fields_dict.ts_countdown) {
			frm._ts_timer_stop = logistics.time_sensitive.timer.mountTimer({
				$wrapper: $(frm.fields_dict.ts_countdown.wrapper),
				deadline: frm.doc.critical_deadline,
				atRiskHours: 4,
				label: __("Deadline"),
			});
		}
		frm.dashboard.clear_headline();
		const caseLink = frm.doc.time_sensitive_case
			? `<a href="/app/time-sensitive-case/${encodeURIComponent(
					frm.doc.time_sensitive_case
			  )}">${frappe.utils.escape_html(frm.doc.time_sensitive_case)}</a>`
			: __("No case linked");
		frm.dashboard.set_headline_alert(
			`${frappe.utils.icon("timer", "sm")} ${__("Time Sensitive")} — ${caseLink}`,
			"orange"
		);
	}

	if (frm.doc.is_time_sensitive && !frm.doc.time_sensitive_case && !frm.is_new()) {
		frm.add_custom_button(__("Create Time Sensitive Case"), () => {
			frappe.prompt(
				[
					{
						fieldname: "case_type",
						fieldtype: "Link",
						options: "Time Sensitive Case Type",
						label: __("Case Type"),
						reqd: 1,
					},
					{
						fieldname: "critical_deadline",
						fieldtype: "Datetime",
						label: __("Critical Deadline"),
						default: frm.doc.critical_deadline || frappe.datetime.add_to_date(frappe.datetime.now_datetime(), { hours: 24 }),
						reqd: 1,
					},
				],
				(values) => {
					frappe.call({
						method: "logistics.time_sensitive.api.create_case_from_document",
						args: {
							doctype: frm.doctype,
							docname: frm.docname,
							case_type: values.case_type,
							critical_deadline: values.critical_deadline,
						},
						freeze: true,
						callback(r) {
							if (r.message && r.message.name) {
								frm.reload_doc();
								frappe.set_route("Form", "Time Sensitive Case", r.message.name);
							}
						},
					});
				},
				__("New Time Sensitive Case")
			);
		}, __("Time Sensitive"));
	}

	if (frm.doc.time_sensitive_case) {
		frm.add_custom_button(__("Open Case"), () => {
			frappe.set_route("Form", "Time Sensitive Case", frm.doc.time_sensitive_case);
		}, __("Time Sensitive"));

		if (frm.doctype === "Sales Quote" && cint(frm.doc.docstatus) === 0) {
			frm.add_custom_button(__("Fetch from Time Sensitive Case"), () => {
				function open() {
					if (!logistics.show_ts_sq_fetch_dialog) {
						frappe.msgprint({
							message: __(
								"Fetch dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."
							),
							indicator: "orange",
						});
						return;
					}
					logistics.show_ts_sq_fetch_dialog(frm, { direction: "case_to_quote" });
				}
				if (logistics.show_ts_sq_fetch_dialog) {
					open();
					return;
				}
				frappe.require("/assets/logistics/js/ts_sq_fetch_dialog.js", open);
			}, __("Get Items"));
		}
	}
};

const TS_OPERATIONAL_DOCTYPES = [
	"Sales Quote",
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration Order",
	"Declaration",
	"Inbound Order",
	"Release Order",
	"VAS Order",
	"Cross-Docking Order",
	"Warehouse Job",
];

TS_OPERATIONAL_DOCTYPES.forEach((dt) => {
	frappe.ui.form.on(dt, {
		refresh(frm) {
			logistics.time_sensitive.setup_operational_form(frm);
		},
		is_time_sensitive(frm) {
			if (cint(frm.doc.is_time_sensitive) && !frm.doc.time_sensitive_case && !frm.is_new()) {
				frappe.show_alert({
					message: __(
						"Marked Time Sensitive — create or attach a case from the Time Sensitive menu."
					),
					indicator: "orange",
				});
			}
			logistics.time_sensitive.setup_operational_form(frm);
		},
	});
});
