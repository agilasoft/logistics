/**
 * Profitability (from GL) section on job/shipment forms.
 * Loads HTML from General Ledger by job_number and displays in profitability_section_html field.
 */
frappe.provide("logistics.profitability");

logistics.profitability.PROFITABILITY_DOCTYPES = [
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Declaration",
	"General Job"
];

logistics.profitability.load_profitability_html = function(frm) {
	var CONTAINER_ID = "logistics-profitability-html-container";

	// Find the HTML field's wrapper or create a dedicated container
	function get_profitability_container() {
		// Prefer the real ControlHTML $wrapper (same node set_value uses) — avoids binding the wrong element.
		var ctrl = frm.fields_dict && frm.fields_dict.profitability_section_html;
		if (ctrl && ctrl.$wrapper && ctrl.$wrapper.length) {
			return ctrl.$wrapper;
		}

		var $layout = (frm.layout && frm.layout.wrapper) ? frm.layout.wrapper : null;
		var $form = frm.wrapper ? $(frm.wrapper) : null;
		var $scope = $layout && $layout.length ? $layout : ($form && $form.length ? $form : null);
		if (!$scope || !$scope.length) {
			return null;
		}

		// Try multiple selectors (Frappe version / structure can vary)
		var $w = $scope.find("[data-fieldname=\"profitability_section_html\"]").first();
		if (!$w.length) $w = $scope.find(".frappe-control[data-fieldname=\"profitability_section_html\"]").first();
		if ($w.length) {
			return $w;
		}

		// Fallback: find section containing profitability section break and inject our div
		var $sectionBreak = $scope.find("[data-fieldname=\"profitability_section_break\"]").first();
		if ($sectionBreak.length) {
			var $section = $sectionBreak.closest(".form-section");
			if ($section.length) {
				var $existing = $section.find("#" + CONTAINER_ID);
				if ($existing.length) {
					return $existing;
				}
				var $inject = $("<div id=\"" + CONTAINER_ID + "\" class=\"frappe-control\" data-fieldname=\"profitability_section_html\"></div>");
				$section.find(".section-body").append($inject);
				return $inject;
			}
		}
		return null;
	}

	function set_html(html) {
		var s = html || "";
		var $container = get_profitability_container();
		if ($container && $container.length) {
			$container.html(s);
		}
		// Keep control in sync if it exists
		var control = frm.fields_dict.profitability_section_html;
		if (control) {
			if (control.set_value) {
				control.set_value(s);
			} else {
				frm.set_df_property("profitability_section_html", "options", s);
				frm.refresh_field("profitability_section_html");
			}
		}
	}

	if (!frm.doc.job_number || !frm.doc.company) {
		set_html("<p class=\"text-muted\">" + __("Set Job Number and Company to load profitability from General Ledger.") + "</p>");
		return;
	}

	// Show loading state immediately so we know the section can display content
	set_html("<p class=\"text-muted\"><i class=\"fa fa-spinner fa-spin\"></i> " + __("Loading profitability...") + "</p>");

	frappe.call({
		method: "logistics.job_management.api.get_job_profitability_html",
		args: {
			job_number: frm.doc.job_number,
			company: frm.doc.company
		},
		callback: function(r) {
			var html = "";
			if (r.exc) {
				var errMsg = r.exc;
				try {
					if (r._server_messages) errMsg = JSON.parse(r._server_messages).message || errMsg;
				} catch (e) { /* ignore */ }
				html = "<p class=\"text-danger\">" + __("Error loading profitability: ") + errMsg + "</p>";
			} else {
				html = (r.message != null && r.message !== undefined) ? String(r.message) : "";
			}
			set_html(html);
		}
	});
};

var doctypes = logistics.profitability.PROFITABILITY_DOCTYPES;
function is_profitability_doctype(doctype) {
	return doctypes && doctypes.indexOf(doctype) !== -1;
}

// Frappe looks up handlers by single doctype (handlers["Air Shipment"]["refresh"]), not by array.
// So we must register each doctype individually.
var form_handlers = {
	onload: function(frm) {
		logistics.profitability.load_profitability_html(frm);
	},
	refresh: function(frm) {
		setTimeout(function() { logistics.profitability.load_profitability_html(frm); }, 150);
	},
	job_number: function(frm) {
		logistics.profitability.load_profitability_html(frm);
	},
	company: function(frm) {
		logistics.profitability.load_profitability_html(frm);
	}
};
for (var i = 0; i < doctypes.length; i++) {
	frappe.ui.form.on(doctypes[i], form_handlers);
}

// Backup: document-level form-refresh
$(document).on("form-refresh", function(e, frm) {
	if (!frm || !is_profitability_doctype(frm.doctype)) return;
	setTimeout(function() { logistics.profitability.load_profitability_html(frm); }, 200);
});

// Fallback: when route changes, poll for cur_frm and run once form is ready (handles cases where events don't fire)
function try_load_on_form_ready() {
	if (typeof frappe === "undefined" || !frappe.cur_frm) return;
	var frm = frappe.cur_frm;
	if (!frm.doctype || !is_profitability_doctype(frm.doctype)) return;
	setTimeout(function() { logistics.profitability.load_profitability_html(frm); }, 300);
}
if (frappe.router && typeof frappe.router.on === "function") {
	frappe.router.on("change", function() {
		setTimeout(try_load_on_form_ready, 100);
		setTimeout(try_load_on_form_ready, 500);
		setTimeout(try_load_on_form_ready, 1200);
	});
}
// Also run when form wrapper fires render_complete (form.js triggers this after refresh)
$(document).on("render_complete", function(e) {
	var frm = e.target && e.target.fieldobj && e.target.fieldobj.frm;
	if (!frm) frm = frappe.cur_frm;
	if (frm && is_profitability_doctype(frm.doctype)) {
		setTimeout(function() { logistics.profitability.load_profitability_html(frm); }, 100);
	}
});

