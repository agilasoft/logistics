/**
 * Shared GL profitability loader for project-level forms.
 *
 * Special Project and MICE Project bind the lazy tab loader in their own
 * doctype scripts and call logistics.profitability.load_project_profitability_html.
 */
frappe.provide("logistics.profitability");

// MICE Project binds the lazy tab loader in mice_project.js (same pattern as Special Project).
logistics.profitability.PROJECT_PROFITABILITY_DOCTYPES = [];

logistics.profitability.load_project_profitability_html = function (frm, opts) {
	opts = opts || {};
	if (!frm || !frm.doc) {
		if (opts.done) {
			opts.done();
		}
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

	function finish() {
		if (opts.done) {
			opts.done();
		}
	}

	function reveal_profitability_section() {
		var control = frm.fields_dict && frm.fields_dict.profitability_section_html;
		if (control && control.$wrapper) {
			control.$wrapper.removeClass("hide-control");
			control.$wrapper
				.closest(".form-section")
				.removeClass("empty-section")
				.addClass("visible-section");
		}
		if (frm.layout && frm.layout.refresh_sections) {
			frm.layout.refresh_sections();
		}
	}

	function set_html(html) {
		var s = html || "";
		reveal_profitability_section();
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
		reveal_profitability_section();
	}

	if (frm.doc.__islocal || !frm.doc.name) {
		set_html(
			"<p class=\"text-muted\">" +
				__("Save this {0} to view profitability from General Ledger.", [
					__(frm.doctype),
				]) +
				"</p>"
		);
		finish();
		return;
	}

	var is_exhibit = frm.doctype === "MICE Project";

	var loading_msg = is_exhibit
		? __("Loading exhibit profitability...")
		: __("Loading project profitability...");
	set_html(
		"<p class=\"text-muted\"><i class=\"fa fa-spinner fa-spin\"></i> " +
			loading_msg +
			"</p>"
	);

	var call_method = is_exhibit
		? "logistics.mice.doctype.mice_project.mice_project_profitability.get_exhibit_profitability_html"
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
	}).always(finish);
};

var project_doctypes = logistics.profitability.PROJECT_PROFITABILITY_DOCTYPES;

function is_project_profitability_doctype(doctype) {
	return project_doctypes && project_doctypes.indexOf(doctype) !== -1;
}

function _bind_project_profitability_tab(frm) {
	if (!frm || !is_project_profitability_doctype(frm.doctype)) {
		return;
	}
	if (window.logistics && logistics.bind_lazy_tab_loader) {
		logistics.bind_lazy_tab_loader(
			frm,
			"profitability_tab",
			"profitability",
			logistics.profitability.load_project_profitability_html
		);
		// Tab may already be active before refresh handlers run (hash / set_tab_as_active).
		if (
			logistics.is_form_tab_active &&
			logistics.is_form_tab_active(frm, "profitability_tab")
		) {
			logistics.trigger_lazy_tab_loaders(frm, "profitability_tab");
		}
	}
}

function _reload_project_profitability_if_active(frm) {
	if (!frm || !is_project_profitability_doctype(frm.doctype)) {
		return;
	}
	if (window.logistics && logistics.invalidate_lazy_tab_loaders) {
		logistics.invalidate_lazy_tab_loaders(frm, ["profitability"]);
	}
	if (
		window.logistics &&
		logistics.is_form_tab_active &&
		logistics.is_form_tab_active(frm, "profitability_tab")
	) {
		logistics.profitability.load_project_profitability_html(frm, { force: true });
	}
}

var project_form_handlers = {
	refresh: function (frm) {
		_bind_project_profitability_tab(frm);
	},
	on_tab_change: function (frm) {
		var tab = frm.get_active_tab && frm.get_active_tab();
		var fieldname = tab && tab.df && tab.df.fieldname;
		if (
			fieldname === "profitability_tab" &&
			window.logistics &&
			logistics.trigger_lazy_tab_loaders
		) {
			logistics.trigger_lazy_tab_loaders(frm, fieldname);
		}
	},
	project: function (frm) {
		_reload_project_profitability_if_active(frm);
	},
	company: function (frm) {
		_reload_project_profitability_if_active(frm);
	},
};

for (var i = 0; i < project_doctypes.length; i++) {
	frappe.ui.form.on(project_doctypes[i], project_form_handlers);
}
