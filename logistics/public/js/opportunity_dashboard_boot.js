// Copyright (c) 2026, Agilasoft and contributors
// Desk-wide Opportunity dashboard loader (app_include_js).

frappe.provide("logistics.opportunity_dashboard");

(function () {
	"use strict";

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

	function logistics_opp_dashboard_should_load(frm) {
		if ((window.location.hash || "").replace("#", "") === LOG_OPP_DASH_TAB) {
			return true;
		}
		return logistics_opp_dashboard_is_active(frm);
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

	function logistics_load_opportunity_dashboard(frm, force) {
		if (!frm || frm.doctype !== "Opportunity") {
			return;
		}
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

	logistics.opportunity_dashboard.render = function (frm, force) {
		logistics_load_opportunity_dashboard(frm, !!force);
	};
	logistics.opportunity_dashboard.invalidate = function (frm) {
		if (frm) {
			frm._logistics_opp_dashboard_cache_version = null;
		}
	};

	window.logistics_load_opportunity_dashboard = logistics_load_opportunity_dashboard;
	window.logistics_opp_dashboard_paint = logistics_opp_dashboard_paint;
	window.logistics_opp_dashboard_mount = logistics_opp_dashboard_mount;
	window.logistics_opp_dashboard_should_load = logistics_opp_dashboard_should_load;
	window.logistics_opp_dashboard_restore = logistics_opp_dashboard_restore;
	window.logistics_bind_opportunity_dashboard_tab = logistics_bind_opportunity_dashboard_tab;
	window.logistics_bind_opportunity_dashboard_refresh_guard = logistics_bind_opportunity_dashboard_refresh_guard;

	function boot_opportunity_dashboard(frm) {
		if (!frm || frm.doctype !== "Opportunity") {
			return;
		}
		if (frm.layout && frm.layout.select_tab && (window.location.hash || "").indexOf(LOG_OPP_DASH_TAB) >= 0) {
			try {
				frm.layout.select_tab(LOG_OPP_DASH_TAB);
			} catch (e) {
				/* ignore */
			}
		}
		logistics_bind_opportunity_dashboard_tab(frm);
		logistics_bind_opportunity_dashboard_refresh_guard(frm);
		if (logistics_opp_dashboard_should_load(frm)) {
			setTimeout(function () {
				logistics_load_opportunity_dashboard(frm, true);
			}, 150);
		}
	}

	$(document).on("form-load.logistics_opp_dashboard", function (_event, frm) {
		boot_opportunity_dashboard(frm);
	});

	frappe.ui.form.on("Opportunity", {
		onload_post_render(frm) {
			boot_opportunity_dashboard(frm);
		},
		on_tab_change(frm) {
			if (logistics_opp_dashboard_should_load(frm)) {
				setTimeout(function () {
					logistics_load_opportunity_dashboard(frm, true);
				}, 120);
			}
		},
	});
})();
