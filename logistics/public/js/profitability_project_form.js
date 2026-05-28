/**
 * Project-level Profitability tab for Special Project & Exhibit.
 *
 * Loads HTML from General Ledger by Project (and Job Number fallback for legacy
 * rows) and renders it inside the ``profitability_section_html`` field on the
 * Profitability tab.
 *
 * Mirrors the robust container-detection / retry pattern used by
 * ``profitability_form.js`` (job-level loader) so the Profitability tab also
 * paints reliably when the user opens it before form fields are fully wired up.
 */
frappe.provide("logistics.profitability");

logistics.profitability.PROJECT_PROFITABILITY_DOCTYPES = [
	"Special Project",
	"Exhibit",
];

logistics.profitability.load_project_profitability_html = function (frm) {
	if (!frm || !frm.doc) {
		return;
	}

	var CONTAINER_ID = "logistics-project-profitability-html-container";

	function get_profitability_container() {
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

		var $w = $scope.find("[data-fieldname=\"profitability_section_html\"]").first();
		if (!$w.length) {
			$w = $scope.find(".frappe-control[data-fieldname=\"profitability_section_html\"]").first();
		}
		if ($w.length) {
			return $w;
		}

		var $sectionBreak = $scope.find("[data-fieldname=\"profitability_section_break\"]").first();
		if ($sectionBreak.length) {
			var $section = $sectionBreak.closest(".form-section");
			if ($section.length) {
				var $existing = $section.find("#" + CONTAINER_ID);
				if ($existing.length) {
					return $existing;
				}
				var $inject = $(
					"<div id=\"" + CONTAINER_ID + "\" class=\"frappe-control\" " +
					"data-fieldname=\"profitability_section_html\"></div>"
				);
				$section.find(".section-body").append($inject);
				return $inject;
			}
		}

		var $tab = $scope.find("[data-fieldname=\"profitability_tab\"]").first();
		if ($tab.length) {
			var $tabPane = $($tab.attr("aria-controls") ? "#" + $tab.attr("aria-controls") : "");
			if ($tabPane && $tabPane.length) {
				var $existing2 = $tabPane.find("#" + CONTAINER_ID);
				if ($existing2.length) {
					return $existing2;
				}
				var $inject2 = $(
					"<div id=\"" + CONTAINER_ID + "\" class=\"frappe-control\" " +
					"data-fieldname=\"profitability_section_html\"></div>"
				);
				$tabPane.append($inject2);
				return $inject2;
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
		var control = frm.fields_dict && frm.fields_dict.profitability_section_html;
		if (control) {
			if (control.set_value) {
				control.set_value(s);
			} else {
				frm.set_df_property("profitability_section_html", "options", s);
				frm.refresh_field("profitability_section_html");
			}
		}
	}

	if (frm.doc.__islocal || !frm.doc.name) {
		set_html(
			"<p class=\"text-muted\">" +
				__("Save this {0} to view profitability from General Ledger.", [
					__(frm.doctype),
				]) +
				"</p>"
		);
		return;
	}

	// Exhibit profitability sums every Docket connected to the Exhibit (mirrors
	// the per-Docket Profitability section, aggregated). Other "project" parents
	// (e.g. Special Project) still use the project-dimension aggregator.
	var is_exhibit = frm.doctype === "Exhibit";
	if (!is_exhibit && !frm.doc.project) {
		set_html(
			"<p class=\"text-muted\">" +
				__("This {0} is not linked to an ERPNext Project yet — profitability will be available once a Project is created/linked.", [
					__(frm.doctype),
				]) +
				"</p>"
		);
		return;
	}

	var loading_msg = is_exhibit
		? __("Loading exhibit profitability...")
		: __("Loading project profitability...");
	set_html(
		"<p class=\"text-muted\"><i class=\"fa fa-spinner fa-spin\"></i> " +
			loading_msg +
			"</p>"
	);

	var call_method = is_exhibit
		? "logistics.exhibits.doctype.exhibit.exhibit_profitability.get_exhibit_profitability_html"
		: "logistics.job_management.project_profitability.get_project_profitability_html";
	var call_args = is_exhibit
		? { exhibit: frm.doc.name }
		: {
			parent_doctype: frm.doctype,
			parent_name: frm.doc.name,
			project: frm.doc.project,
			company: frm.doc.company || null,
		};

	frappe.call({
		method: call_method,
		args: call_args,
		callback: function (r) {
			var html = "";
			if (r.exc) {
				var errMsg = r.exc;
				try {
					if (r._server_messages) {
						errMsg = JSON.parse(r._server_messages).message || errMsg;
					}
				} catch (e) {
					/* ignore */
				}
				var err_prefix = is_exhibit
					? __("Error loading exhibit profitability: ")
					: __("Error loading project profitability: ");
				html = "<p class=\"text-danger\">" + err_prefix + errMsg + "</p>";
			} else {
				html = r.message != null && r.message !== undefined ? String(r.message) : "";
			}
			set_html(html);
		},
	});
};

var project_doctypes = logistics.profitability.PROJECT_PROFITABILITY_DOCTYPES;

function is_project_profitability_doctype(doctype) {
	return project_doctypes && project_doctypes.indexOf(doctype) !== -1;
}

// Stagger reload attempts to survive the field/tab not being wired up yet.
function queue_project_profitability_load(frm) {
	if (!frm || !is_project_profitability_doctype(frm.doctype)) return;
	setTimeout(function () {
		logistics.profitability.load_project_profitability_html(frm);
	}, 150);
	setTimeout(function () {
		logistics.profitability.load_project_profitability_html(frm);
	}, 600);
	setTimeout(function () {
		logistics.profitability.load_project_profitability_html(frm);
	}, 1500);
}

var project_form_handlers = {
	onload: function (frm) {
		queue_project_profitability_load(frm);
	},
	refresh: function (frm) {
		queue_project_profitability_load(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper
				.off("click.project_profitability")
				.on(
					"click.project_profitability",
					'[data-fieldname="profitability_tab"]',
					function () {
						setTimeout(function () {
							logistics.profitability.load_project_profitability_html(frm);
						}, 50);
					}
				);
		}
	},
	project: function (frm) {
		logistics.profitability.load_project_profitability_html(frm);
	},
	company: function (frm) {
		logistics.profitability.load_project_profitability_html(frm);
	},
};

for (var i = 0; i < project_doctypes.length; i++) {
	frappe.ui.form.on(project_doctypes[i], project_form_handlers);
}

// Belt-and-braces: router change can leave us without form-level events firing.
if (frappe.router && typeof frappe.router.on === "function") {
	frappe.router.on("change", function () {
		setTimeout(function () {
			var frm = frappe.cur_frm;
			if (frm && is_project_profitability_doctype(frm.doctype)) {
				queue_project_profitability_load(frm);
			}
		}, 400);
	});
}

$(document).on("form-refresh", function (e, frm) {
	if (!frm || !is_project_profitability_doctype(frm.doctype)) return;
	queue_project_profitability_load(frm);
});

$(document).on("render_complete", function (e) {
	var frm = e.target && e.target.fieldobj && e.target.fieldobj.frm;
	if (!frm) frm = frappe.cur_frm;
	if (frm && is_project_profitability_doctype(frm.doctype)) {
		setTimeout(function () {
			logistics.profitability.load_project_profitability_html(frm);
		}, 100);
	}
});
