// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.provide("logistics.opportunity_dashboard");

const LOG_OPP_DASH_TAB = "custom_dashboard_tab";
const LOG_OPP_DASH_MOUNT = "log-opp-dashboard-mount";
const LOG_OPP_DASH_ROOT = "log-opp-dash";
const LOG_OPP_DASH_CACHE_VERSION = 3;

function logistics_opp_dashboard_tab_pane(frm) {
	if (frm.layout && frm.layout.tabs) {
		for (let i = 0; i < frm.layout.tabs.length; i++) {
			const tab = frm.layout.tabs[i];
			if (tab.df && tab.df.fieldname === LOG_OPP_DASH_TAB && tab.wrapper) {
				return tab.wrapper;
			}
		}
	}
	return $();
}

function logistics_opp_dashboard_mount(frm) {
	const control = frm.fields_dict && frm.fields_dict.custom_opportunity_dashboard_html;
	if (control && control.$wrapper && control.$wrapper.length) {
		control.$wrapper
			.closest(".form-section")
			.removeClass("empty-section hide-control hide")
			.addClass("visible-section");
		return control.$wrapper;
	}

	const $pane = logistics_opp_dashboard_tab_pane(frm);
	if (!$pane.length) {
		return $();
	}
	$pane.removeClass("hide empty-section").addClass("show active visible-section");
	let $mount = $pane.children("#" + LOG_OPP_DASH_MOUNT);
	if (!$mount.length) {
		$mount = $(
			'<div id="' + LOG_OPP_DASH_MOUNT + '" class="form-section visible-section" ' +
				'style="min-height:240px;padding:0;"></div>'
		);
		$pane.prepend($mount);
	}
	if (frm.layout && frm.layout.tabs) {
		frm.layout.tabs.forEach(function (tab) {
			if (tab.df && tab.df.fieldname === LOG_OPP_DASH_TAB && typeof tab.toggle === "function") {
				tab.toggle(true);
			}
		});
	}
	return $mount;
}

function logistics_opp_dashboard_is_active(frm) {
	const tab = frm.get_active_tab && frm.get_active_tab();
	if (tab && tab.df && tab.df.fieldname === LOG_OPP_DASH_TAB) {
		return true;
	}
	const $pane = logistics_opp_dashboard_tab_pane(frm);
	return $pane.length && ($pane.hasClass("active") || $pane.hasClass("show"));
}

function logistics_opp_dashboard_paint(frm, html) {
	const $mount = logistics_opp_dashboard_mount(frm);
	if (!$mount.length) {
		return false;
	}
	frm._logistics_opp_dashboard_html_cache = html || "";
	frm._logistics_opp_dashboard_cache_version = LOG_OPP_DASH_CACHE_VERSION;
	$mount.html(html || "");
	$mount.off("click.log-opp-dash");
	$mount.on("click.log-opp-dash", "." + LOG_OPP_DASH_ROOT + "__toggle button", function () {
		const metric = $(this).attr("data-metric");
		if (!metric) {
			return;
		}
		frm._logistics_opp_dashboard_metric = metric;
		logistics_load_opportunity_dashboard(frm, true);
	});
	return true;
}

function logistics_opp_dashboard_should_load(frm) {
	if ((window.location.hash || "").replace("#", "") === LOG_OPP_DASH_TAB) {
		return true;
	}
	return logistics_opp_dashboard_is_active(frm);
}

function logistics_opp_dashboard_restore(frm) {
	if (!logistics_opp_dashboard_should_load(frm)) {
		return;
	}
	const cache_ok =
		frm._logistics_opp_dashboard_cache_version === LOG_OPP_DASH_CACHE_VERSION &&
		frm._logistics_opp_dashboard_html_cache;
	const $mount = logistics_opp_dashboard_mount(frm);
	const needs_paint = $mount.length && !$mount.find("." + LOG_OPP_DASH_ROOT).length;
	if (cache_ok && needs_paint) {
		logistics_opp_dashboard_paint(frm, frm._logistics_opp_dashboard_html_cache);
		return;
	}
	if (cache_ok && !needs_paint) {
		return;
	}
	logistics_load_opportunity_dashboard(frm, true);
}

function logistics_bind_opportunity_dashboard_refresh_guard(frm) {
	if (frm._logistics_opp_dashboard_refresh_guard) {
		return;
	}
	frm._logistics_opp_dashboard_refresh_guard = true;
	$(frm.wrapper).on("refresh-fields.log_opp_dashboard", function () {
		setTimeout(function () {
			logistics_opp_dashboard_restore(frm);
		}, 0);
	});
}

function logistics_load_opportunity_dashboard(frm, force) {
	if (frm._logistics_opp_dashboard_loading && !force) {
		return;
	}

	const scopes = frm.doc.custom_opportunity_scopes || [];
	if (!scopes.length) {
		logistics_opp_dashboard_paint(
			frm,
			'<div class="' + LOG_OPP_DASH_ROOT + '"><div class="' + LOG_OPP_DASH_ROOT + '__empty">' +
				__("Add scopes on the Services tab with annual opportunity values to see attainment.") +
				"</div></div>"
		);
		return;
	}
	if (!frm.doc.company) {
		logistics_opp_dashboard_paint(
			frm,
			'<div class="' + LOG_OPP_DASH_ROOT + '"><div class="' + LOG_OPP_DASH_ROOT + '__empty">' +
				__("Set Company to load the dashboard.") +
				"</div></div>"
		);
		return;
	}

	logistics_opp_dashboard_paint(
		frm,
		'<div class="' + LOG_OPP_DASH_ROOT + '"><div class="' + LOG_OPP_DASH_ROOT + '__empty">' +
			'<i class="fa fa-spinner fa-spin"></i> ' + __("Loading dashboard…") +
			"</div></div>"
	);

	const args = {
		company: frm.doc.company,
		metric: frm._logistics_opp_dashboard_metric || null,
	};
	if (frm.doc.name && !frm.is_new()) {
		args.opportunity = frm.doc.name;
	} else {
		args.scopes = JSON.stringify(scopes);
		if (frm.doc.opportunity_from === "Customer" && frm.doc.party_name) {
			args.customer = frm.doc.party_name;
		}
	}

	frm._logistics_opp_dashboard_loading = true;
	frappe.call({
		method: "logistics.pricing_center.api.opportunity_dashboard.get_opportunity_dashboard_html",
		args,
		freeze: false,
		callback(r) {
			if (r.exc) {
				logistics_opp_dashboard_paint(
					frm,
					'<div class="' + LOG_OPP_DASH_ROOT + '"><div class="' + LOG_OPP_DASH_ROOT + '__empty">' +
						__("Could not load dashboard. Please refresh and try again.") +
						"</div></div>"
				);
				return;
			}
			if (r.message) {
				logistics_opp_dashboard_paint(frm, r.message);
			}
		},
		error() {
			logistics_opp_dashboard_paint(
				frm,
				'<div class="' + LOG_OPP_DASH_ROOT + '"><div class="' + LOG_OPP_DASH_ROOT + '__empty">' +
					__("Could not load dashboard. Please refresh and try again.") +
					"</div></div>"
			);
		},
		always() {
			frm._logistics_opp_dashboard_loading = false;
		},
	});
}

function logistics_bind_opportunity_dashboard_tab(frm) {
	if (!frm.layout || !frm.layout.wrapper) {
		return;
	}
	frm.layout.wrapper
		.off("click.log_opp_dashboard_tab")
		.on("click.log_opp_dashboard_tab", '[data-fieldname="' + LOG_OPP_DASH_TAB + '"]', function () {
			setTimeout(function () {
				logistics_load_opportunity_dashboard(frm, true);
			}, 80);
		});
}

logistics.opportunity_dashboard = logistics.opportunity_dashboard || {};
logistics.opportunity_dashboard.render = function (frm) {
	logistics_load_opportunity_dashboard(frm, true);
};
logistics.opportunity_dashboard.invalidate = function (frm) {
	if (frm) {
		frm._logistics_opp_dashboard_cache_version = null;
	}
};

function logistics_refresh_opportunity_dashboard(frm) {
	if (logistics_opp_dashboard_should_load(frm)) {
		logistics_load_opportunity_dashboard(frm, true);
	}
}

frappe.ui.form.on("Opportunity", {
	setup(frm) {
		if (typeof logistics_setup_opportunity_scope_queries === "function") {
			logistics_setup_opportunity_scope_queries(frm);
		}
	},
	onload(frm) {
		if (typeof logistics_setup_opportunity_scope_queries === "function") {
			logistics_setup_opportunity_scope_queries(frm);
		}
	},
	refresh(frm) {
		const has_scopes = !!(frm.fields_dict && frm.fields_dict.custom_opportunity_scopes);
		if (has_scopes) {
			if (typeof logistics_setup_opportunity_scope_queries === "function") {
				logistics_setup_opportunity_scope_queries(frm);
			}
			logistics_update_opportunity_scope_totals(frm);
		}
		if (frm.fields_dict && frm.fields_dict.custom_dashboard_tab) {
			logistics_bind_opportunity_dashboard_tab(frm);
			logistics_bind_opportunity_dashboard_refresh_guard(frm);
		}
		if (logistics_opp_dashboard_should_load(frm)) {
			setTimeout(function () {
				logistics_load_opportunity_dashboard(frm, true);
			}, 300);
		}
	},
	onload_post_render(frm) {
		if (logistics_opp_dashboard_should_load(frm)) {
			setTimeout(function () {
				logistics_load_opportunity_dashboard(frm, true);
			}, 200);
		}
	},
	on_tab_change(frm) {
		if (logistics_opp_dashboard_should_load(frm)) {
			setTimeout(function () {
				logistics_load_opportunity_dashboard(frm, true);
			}, 120);
		}
	},
	custom_opportunity_scopes_on_form_rendered(frm) {
		if (typeof logistics_setup_opportunity_scope_queries === "function") {
			logistics_setup_opportunity_scope_queries(frm);
		}
	},
	custom_opportunity_scopes_add(frm, cdt, cdn) {
		if (typeof logistics_setup_opportunity_scope_queries === "function") {
			logistics_setup_opportunity_scope_queries(frm);
		}
		if (typeof logistics_refresh_scope_row_dependencies === "function") {
			setTimeout(() => logistics_refresh_scope_row_dependencies(frm, cdt, cdn), 0);
		}
	},
	party_name(frm) {
		logistics_refresh_opportunity_scope_actuals(frm);
		logistics_refresh_opportunity_dashboard(frm);
	},
	company(frm) {
		logistics_refresh_opportunity_scope_actuals(frm);
		logistics_refresh_opportunity_dashboard(frm);
	},
});

window.logistics_load_opportunity_dashboard = logistics_load_opportunity_dashboard;
window.logistics_opp_dashboard_paint = logistics_opp_dashboard_paint;
window.logistics_opp_dashboard_mount = logistics_opp_dashboard_mount;

frappe.ui.form.on("Opportunity Service Scope", {
	opportunity_value(frm) {
		logistics_update_opportunity_scope_totals(frm);
		logistics_refresh_opportunity_dashboard(frm);
	},
	custom_opportunity_scopes_remove(frm) {
		logistics_update_opportunity_scope_totals(frm);
		logistics_refresh_opportunity_scope_actuals(frm);
		logistics_refresh_opportunity_dashboard(frm);
	},
});

function logistics_update_opportunity_scope_totals(frm) {
	if (!frm.fields_dict.custom_opportunity_scopes) {
		return;
	}
	let total_value = 0;
	let total_revenue = 0;
	let total_profit = 0;
	(frm.doc.custom_opportunity_scopes || []).forEach((row) => {
		total_value += flt(row.opportunity_value);
		total_revenue += flt(row.actual_revenue);
		total_profit += flt(row.actual_profit);
	});
	frm.set_value("custom_total_scope_opportunity_value", total_value);
	frm.set_value("custom_total_scope_actual_revenue", total_revenue);
	frm.set_value("custom_total_scope_actual_profit", total_profit);
	if ((frm.doc.custom_opportunity_scopes || []).length && total_value) {
		frm.set_value("opportunity_amount", total_value);
	}
}

function logistics_refresh_opportunity_scope_actuals(frm) {
	if (!frm.fields_dict.custom_opportunity_scopes) {
		return;
	}
	const scopes = frm.doc.custom_opportunity_scopes || [];
	if (!scopes.length || !frm.doc.company) {
		return;
	}

	const customer =
		frm.doc.opportunity_from === "Customer" ? frm.doc.party_name : null;
	if (!customer) {
		return;
	}

	const args = { company: frm.doc.company, customer, scopes: JSON.stringify(scopes) };
	if (frm.doc.name && !frm.is_new()) {
		args.opportunity = frm.doc.name;
	}

	frappe.call({
		method: "logistics.pricing_center.api.opportunity_scopes.get_opportunity_scope_actuals",
		args,
		async: true,
		callback(r) {
			if (!r.message) {
				return;
			}
			(r.message.scopes || []).forEach((computed) => {
				const row = scopes.find((s) => s.name === computed.name);
				if (row) {
					row.actual_revenue = computed.actual_revenue;
					row.actual_profit = computed.actual_profit;
				}
			});
			frm.set_value(
				"custom_total_scope_actual_revenue",
				r.message.custom_total_scope_actual_revenue
			);
			frm.set_value("custom_total_scope_actual_profit", r.message.custom_total_scope_actual_profit);
			logistics_update_opportunity_scope_totals(frm);
			logistics_refresh_opportunity_dashboard(frm);
		},
	});
}
