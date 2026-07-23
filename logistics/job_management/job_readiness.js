// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt
//
// Action → Check Job Readiness — structured checklist for submit / complete / close gates.

frappe.provide("logistics.job_readiness");

var JOB_READINESS_DOCTYPES = [
	"Transport Job",
	"Sea Shipment",
	"Air Shipment",
	"Warehouse Job",
	"Declaration",
];

function _jr_escape(s) {
	return frappe.utils.escape_html(String(s == null ? "" : s));
}

function _jr_infer_gate(frm) {
	var d = frm.doc;
	if (!d) {
		return "submit";
	}
	var statusField =
		frm.doctype === "Transport Job" ? "status" : "job_status";
	var cur = (d[statusField] || "").toString().trim().toLowerCase();
	if (cur === "completed" || cur === "reopened" || cur === "closed") {
		return "close";
	}
	if (cint(d.docstatus) === 1) {
		return "complete";
	}
	return "submit";
}

function _jr_build_html(result) {
	var errors = result.errors || [];
	var warnings = result.warnings || [];
	var parts = [];
	parts.push(
		"<p><strong>" +
			__("Gate") +
			":</strong> " +
			_jr_escape(result.gate) +
			" &nbsp;|&nbsp; " +
			(result.ok
				? "<span class='text-success'>" + __("Ready") + "</span>"
				: "<span class='text-danger'>" + __("Not ready") + "</span>") +
			"</p>"
	);
	if (result.would_block) {
		parts.push(
			"<p class='text-muted'>" +
				__("Current Logistics Settings would block this transition.") +
				"</p>"
		);
	}
	if (errors.length) {
		parts.push("<h5>" + __("Issues") + "</h5><ul>");
		errors.forEach(function (e) {
			parts.push("<li>" + _jr_escape(e.message || e.code) + "</li>");
		});
		parts.push("</ul>");
	}
	if (warnings.length) {
		parts.push("<h5>" + __("Warnings") + "</h5><ul>");
		warnings.forEach(function (w) {
			parts.push("<li>" + _jr_escape(w.message || w.code) + "</li>");
		});
		parts.push("</ul>");
	}
	if (!errors.length && !warnings.length) {
		parts.push(
			"<p class='text-success'>" +
				__("All checked items look good for this gate.") +
				"</p>"
		);
	}
	return parts.join("");
}

logistics.job_readiness.show = function (frm, gate) {
	gate = gate || _jr_infer_gate(frm);
	frappe.call({
		method: "logistics.job_management.job_readiness.get_job_readiness_summary",
		args: {
			doctype: frm.doctype,
			name: frm.doc.name,
			gate: gate,
		},
		freeze: true,
		callback: function (r) {
			if (r.exc || !r.message) {
				return;
			}
			var result = r.message;
			var d = new frappe.ui.Dialog({
				title: __("Job Readiness"),
				size: "large",
				fields: [
					{
						fieldtype: "HTML",
						fieldname: "readiness_html",
					},
				],
				primary_action_label: __("Close"),
				primary_action: function () {
					d.hide();
				},
			});
			d.fields_dict.readiness_html.$wrapper.html(_jr_build_html(result));
			d.show();
		},
	});
};

logistics.job_readiness.setup = function (frm) {
	if (!frm || !frm.doc || frm.is_new()) {
		return;
	}
	if (typeof frm.remove_custom_button === "function") {
		frm.remove_custom_button(__("Check Job Readiness"), __("Action"));
	}
	frm.add_custom_button(
		__("Check Job Readiness"),
		function () {
			logistics.job_readiness.show(frm);
		},
		__("Action")
	);
};

(function () {
	if (logistics.job_readiness._handlers_registered) {
		return;
	}
	logistics.job_readiness._handlers_registered = true;
	JOB_READINESS_DOCTYPES.forEach(function (dt) {
		frappe.ui.form.on(dt, {
			refresh: function (frm) {
				logistics.job_readiness.setup(frm);
			},
		});
	});
})();
