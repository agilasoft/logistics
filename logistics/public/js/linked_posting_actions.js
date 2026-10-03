// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
//
// Internal Billing and Intercompany Transactions on Linked services.

frappe.provide("logistics.posting");

function _posting_add(frm, opts) {
	if (window.logistics && logistics.menu && typeof logistics.menu.add === "function") {
		return logistics.menu.add(frm, opts);
	}
	return frm.add_custom_button(opts.label, opts.action, opts.group);
}

function _invoice_link(doctype, name) {
	if (!name) {
		return "";
	}
	var label = frappe.utils.escape_html(name);
	if (typeof frappe.utils.get_form_link === "function") {
		return frappe.utils.get_form_link(doctype, name, true, label);
	}
	return label;
}

function _show_intercompany_dialog(message) {
	message = message || {};
	var logs = message.logs || [];
	var errors = message.errors || [];
	var parts = [];
	if (logs.length) {
		parts.push(
			"<table class='table table-bordered table-sm'><thead><tr><th>" +
				__("Job") +
				"</th><th>" +
				__("Sales Invoice") +
				"</th><th>" +
				__("Purchase Invoice") +
				"</th></tr></thead><tbody>"
		);
		logs.forEach(function (row) {
			parts.push(
				"<tr><td>" +
					frappe.utils.escape_html(row.job || "") +
					"</td><td>" +
					_invoice_link("Sales Invoice", row.si) +
					"</td><td>" +
					_invoice_link("Purchase Invoice", row.pi) +
					"</td></tr>"
			);
		});
		parts.push("</tbody></table>");
	} else {
		parts.push(
			"<p>" +
				frappe.utils.escape_html(
					message.message || __("No intercompany invoices were created.")
				) +
				"</p>"
		);
	}
	if (errors.length) {
		parts.push("<p><strong>" + __("Errors") + "</strong></p><ul>");
		errors.forEach(function (err) {
			parts.push("<li>" + frappe.utils.escape_html(err) + "</li>");
		});
		parts.push("</ul>");
	}
	var indicator = "blue";
	if (logs.length && errors.length) {
		indicator = "orange";
	} else if (logs.length) {
		indicator = "green";
	} else if (errors.length) {
		indicator = "red";
	}
	frappe.msgprint({
		title: __("Intercompany Transactions"),
		message: parts.join(""),
		indicator: indicator,
	});
}

function _run_internal_billing(frm) {
	frappe.call({
		method: "logistics.billing.internal_billing.create_internal_billing_for_quote",
		args: {
			sales_quote_name: frm.doc.sales_quote,
			posting_date: frappe.datetime.get_today(),
		},
		callback: function (r) {
			if (!r.message) {
				return;
			}
			var msg = r.message.message || __("Internal billing processed");
			if (r.message.journal_entries && r.message.journal_entries.length) {
				msg = __("Created Journal Entries: {0}.", [r.message.journal_entries.join(", ")]);
			} else if (r.message.journal_entry) {
				msg = __("Created Journal Entry {0}.", [r.message.journal_entry]);
			}
			frappe.show_alert({ message: msg, indicator: "blue" }, 5);
			frm.reload_doc();
		},
	});
}

function _run_intercompany(frm) {
	frappe.call({
		method: "logistics.intercompany.intercompany_invoice.create_intercompany_invoices_for_quote",
		args: {
			sales_quote_name: frm.doc.sales_quote,
			posting_date: frappe.datetime.get_today(),
		},
		callback: function (r) {
			if (!r.message) {
				return;
			}
			_show_intercompany_dialog(r.message);
			frm.reload_doc();
		},
	});
}

/**
 * Add Internal Billing and Intercompany Transactions when this Linked service qualifies.
 * Safe to call from a form refresh. Buttons are added after the server returns the flags.
 */
logistics.posting.add_linked_buttons = function (frm) {
	if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal || !frm.doc.sales_quote) {
		return;
	}
	var docname = frm.doc.name;
	frm._linked_posting_token = (frm._linked_posting_token || 0) + 1;
	var token = frm._linked_posting_token;
	frappe.call({
		method: "logistics.billing.internal_billing.get_linked_posting_actions",
		args: { doctype: frm.doctype, name: docname },
		freeze: false,
		callback: function (r) {
			if (!frm.doc || frm.doc.name !== docname || frm._linked_posting_token !== token) {
				return;
			}
			var flags = r.message || {};
			if (flags.intercompany) {
				_posting_add(frm, {
					label: __("Intercompany Transactions"),
					group: __("Post"),
					ptype: "write",
					also: [
						{ doctype: "Sales Invoice", ptype: "create" },
						{ doctype: "Purchase Invoice", ptype: "create" },
					],
					action: function () {
						_run_intercompany(frm);
					},
				});
			}
			if (flags.internal_billing) {
				_posting_add(frm, {
					label: __("Internal Billing"),
					group: __("Post"),
					ptype: "write",
					also: [{ doctype: "Journal Entry", ptype: "create" }],
					action: function () {
						_run_internal_billing(frm);
					},
				});
			}
		},
	});
};
