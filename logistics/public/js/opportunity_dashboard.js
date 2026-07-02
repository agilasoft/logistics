// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.provide("logistics.opportunity_dashboard");

(function () {
	"use strict";

	const TAB_FIELD = "custom_dashboard_tab";
	const HTML_FIELD = "custom_opportunity_dashboard_html";
	const MOUNT_ID = "log-opp-dashboard-mount";
	const DASH_ROOT = "log-opp-dash";

	function tab_pane(frm) {
		if (!frm.layout || !frm.layout.tabs) {
			return $();
		}
		for (let i = 0; i < frm.layout.tabs.length; i++) {
			const tab = frm.layout.tabs[i];
			if (tab.df && tab.df.fieldname === TAB_FIELD && tab.wrapper) {
				return tab.wrapper;
			}
		}
		const $scope = frm.$wrapper || (frm.layout && frm.layout.wrapper);
		if (!$scope || !$scope.length) {
			return $();
		}
		const tab_id = frappe.router && frappe.router.slug ? frappe.router.slug("Opportunity") : "opportunity";
		let $pane = $scope.find("#" + tab_id + "-" + TAB_FIELD);
		if (!$pane.length) {
			$pane = $scope.find('[data-fieldname="' + TAB_FIELD + '"]').closest(".tab-pane");
		}
		return $pane;
	}

	function ensure_mount(frm) {
		const control = frm.fields_dict && frm.fields_dict[HTML_FIELD];
		if (control && control.$wrapper && control.$wrapper.length) {
			control.$wrapper.closest(".form-section").removeClass("empty-section hide-control").addClass("visible-section");
			return control.$wrapper;
		}

		const $pane = tab_pane(frm);
		if (!$pane.length) {
			return $();
		}

		$pane.removeClass("hide empty-section");
		let $mount = $pane.find("#" + MOUNT_ID);
		if (!$mount.length) {
			$mount = $(
				'<div id="' +
					MOUNT_ID +
					'" class="frappe-control" data-fieldname="' +
					HTML_FIELD +
					'" style="min-height:200px;padding:0;"></div>'
			);
			$pane.prepend($mount);
		}
		return $mount;
	}

	function is_dashboard_tab_active(frm) {
		const tab = frm.get_active_tab && frm.get_active_tab();
		if (tab && tab.df && tab.df.fieldname === TAB_FIELD) {
			return true;
		}
		const $pane = tab_pane(frm);
		return $pane.length && $pane.hasClass("active");
	}

	function reveal_dashboard_tab(frm) {
		const $pane = tab_pane(frm);
		if ($pane.length) {
			$pane.removeClass("empty-section hide-control hide").addClass("visible-section show active");
			$pane.find(".form-section").removeClass("empty-section hide-control").addClass("visible-section");
		}
		if (frm.layout && frm.layout.refresh_tabs) {
			frm.layout.refresh_tabs();
		}
	}

	function set_dashboard_html(frm, html) {
		const $mount = ensure_mount(frm);
		if (!$mount.length) {
			return;
		}
		$mount.html(html || "");
		const control = frm.fields_dict && frm.fields_dict[HTML_FIELD];
		if (control && typeof control.html === "function") {
			control.html(html || "");
		}
		if (frm.set_df_property) {
			try {
				frm.set_df_property(HTML_FIELD, "options", html || "");
			} catch (e) {
				/* injected mount only */
			}
		}
		reveal_dashboard_tab(frm);
		$mount.off("click.log-opp-dash");
		$mount.on("click.log-opp-dash", "." + DASH_ROOT + "__toggle button", function () {
			const metric = $(this).attr("data-metric");
			if (!metric) {
				return;
			}
			frm._logistics_opp_dashboard_metric = metric;
			load_opportunity_dashboard(frm, { force: true });
		});
	}

	function build_call_args(frm) {
		const scopes = frm.doc.custom_opportunity_scopes || [];
		const args = {
			company: frm.doc.company,
			metric: frm._logistics_opp_dashboard_metric || null,
			scopes: JSON.stringify(scopes),
		};
		if (frm.doc.name && !frm.is_new()) {
			args.opportunity = frm.doc.name;
		} else if (frm.doc.opportunity_from === "Customer" && frm.doc.party_name) {
			args.customer = frm.doc.party_name;
		}
		return args;
	}

	function load_opportunity_dashboard(frm, opts) {
		opts = opts || {};
		const scopes = frm.doc.custom_opportunity_scopes || [];

		if (!scopes.length) {
			set_dashboard_html(
				frm,
				'<div class="' + DASH_ROOT + '"><div class="' + DASH_ROOT + '__empty">' +
					__("Add scopes on the Services tab with annual opportunity values to see attainment.") +
					"</div></div>"
			);
			if (opts.done) opts.done();
			return;
		}
		if (!frm.doc.company) {
			set_dashboard_html(
				frm,
				'<div class="' + DASH_ROOT + '"><div class="' + DASH_ROOT + '__empty">' +
					__("Set Company to load the dashboard.") +
					"</div></div>"
			);
			if (opts.done) opts.done();
			return;
		}

		set_dashboard_html(
			frm,
			'<div class="' + DASH_ROOT + '"><div class="' + DASH_ROOT + '__empty">' +
				'<i class="fa fa-spinner fa-spin"></i> ' + __("Loading dashboard…") +
				"</div></div>"
		);

		frappe
			.call({
				method: "logistics.pricing_center.api.opportunity_dashboard.get_opportunity_dashboard_html",
				args: build_call_args(frm),
			})
			.then(function (r) {
				if (r.exc) {
					set_dashboard_html(
						frm,
						'<div class="' + DASH_ROOT + '"><div class="' + DASH_ROOT + '__empty">' +
							__("Could not load dashboard. Please refresh and try again.") +
							"</div></div>"
					);
					return;
				}
				if (r.message) {
					set_dashboard_html(frm, r.message);
				}
			})
			.always(function () {
				if (opts.done) opts.done();
			});
	}

	logistics.opportunity_dashboard.render = function (frm, force) {
		load_opportunity_dashboard(frm, { force: !!force });
	};

	logistics.opportunity_dashboard.invalidate = function () {
		/* no-op: always reload on tab visit */
	};

	function bind_dashboard_tab(frm) {
		if (!frm.layout || !frm.layout.wrapper) {
			return;
		}
		frm.layout.wrapper
			.off("click.opp_dashboard_tab")
			.on("click.opp_dashboard_tab", '[data-fieldname="' + TAB_FIELD + '"]', function () {
				setTimeout(function () {
					load_opportunity_dashboard(frm, { force: true });
				}, 80);
			});
	}

	frappe.ui.form.on("Opportunity", {
		refresh: function (frm) {
			bind_dashboard_tab(frm);
			if (is_dashboard_tab_active(frm)) {
				setTimeout(function () {
					load_opportunity_dashboard(frm, { force: true });
				}, 120);
			}
		},
		on_tab_change: function (frm) {
			if (is_dashboard_tab_active(frm)) {
				setTimeout(function () {
					load_opportunity_dashboard(frm, { force: true });
				}, 80);
			}
		},
	});
})();
