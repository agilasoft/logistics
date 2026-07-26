// Sea Freight Control Tower — loaded via hooks page_js (cache-bustable asset)
// rev: 2026-07-24-sfct-date-range

frappe.provide("logistics.sea_freight_control_tower");

(function () {
	if (logistics.sea_freight_control_tower._hooks_loaded) {
		return;
	}
	logistics.sea_freight_control_tower._hooks_loaded = true;

	const FILTER_DEFS = [
		{ key: "company", label: __("Company"), options: "Company" },
		{ key: "branch", label: __("Branch"), options: "Branch", company_scoped: true },
		{
			key: "cost_center",
			label: __("Cost Center"),
			options: "Cost Center",
			company_scoped: true,
			extra_filters: { is_group: 0 },
		},
		{
			key: "profit_center",
			label: __("Profit Center"),
			options: "Profit Center",
			company_scoped: true,
		},
		{ key: "unloco", label: __("UNLOCO"), options: "UNLOCO" },
	];

	const DEFAULT_PREFS = {
		kpis: {
			show_open_jobs: 1,
			show_avg_age: 1,
			show_handled: 1,
			show_lead_time: 1,
			warn_age_days: 60,
		},
		shipping_lines: { limit: 10 },
		returned: { visible: 1 },
		modules: { visible: 1 },
		links: { visible: 1 },
	};

	function deep_merge_prefs(raw) {
		const prefs = $.extend(true, {}, DEFAULT_PREFS, raw || {});
		prefs.shipping_lines.limit = Math.max(1, Math.min(50, cint(prefs.shipping_lines.limit) || 10));
		prefs.kpis.warn_age_days = Math.max(0, cint(prefs.kpis.warn_age_days) || 0);
		["show_open_jobs", "show_avg_age", "show_handled", "show_lead_time"].forEach((k) => {
			prefs.kpis[k] = cint(prefs.kpis[k]) ? 1 : 0;
		});
		["returned", "modules", "links"].forEach((s) => {
			prefs[s].visible = cint(prefs[s].visible) ? 1 : 0;
		});
		return prefs;
	}

	class SeaFreightControlTowerPage {
		constructor(wrapper) {
			this.wrapper = $(wrapper);
			this.page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Sea Freight Control Tower"),
				single_column: true,
			});
			this.controls = {};
			this.prefs = deep_merge_prefs();
			this._refresh_timer = null;
			this._booting = true;
			this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
			this.make_layout();
			this.mount_filters();
			this.bind_settings();
			this.bind_full_width();
			this._bootstrap();
		}

		make_layout() {
			const gear = `<button type="button" class="sfct-settings-btn" data-sfct-settings title="${__(
				"Settings"
			)}" aria-label="${__("Settings")}">
					<svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
						<path d="M6.5 1.5h3l.4 1.6a4.5 4.5 0 0 1 1.2.7l1.6-.5 1.5 2.6-1.2 1.1c.1.4.1.8 0 1.2l1.2 1.1-1.5 2.6-1.6-.5a4.5 4.5 0 0 1-1.2.7L9.5 14.5h-3l-.4-1.6a4.5 4.5 0 0 1-1.2-.7l-1.6.5L1.8 10l1.2-1.1a4.6 4.6 0 0 1 0-1.2L1.8 6.6l1.5-2.6 1.6.5a4.5 4.5 0 0 1 1.2-.7L6.5 1.5Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
						<circle cx="8" cy="8" r="2" stroke="currentColor" stroke-width="1.2"/>
					</svg>
				</button>`;

			const $ui = $(`
				<div class="sfct">
					<section class="sfct-filters-card">
						<div class="sfct-filters-toolbar">
							<div class="sfct-filters-sub">${__("Scope KPIs by company dimensions")}</div>
							${gear}
						</div>
						<div class="sfct-filters-grid" id="sfct-filters"></div>
					</section>

					<section class="sfct-section-head">
						<div class="sfct-section-title">${__("Key metrics")}</div>
					</section>
					<section class="sfct-kpi-row" id="sfct-kpis" aria-live="polite">
						${this._kpi_skeleton()}
					</section>

					<section class="sfct-panels">
						<article class="sfct-card" id="sfct-shipping_lines-card">
							<div class="sfct-card-head">
								<h2 id="sfct-shipping_lines-title">${__("Top Shipping Lines")}</h2>
								<p>${__("Shipments by shipping line for the selected date range")}</p>
							</div>
							<div id="sfct-shipping_lines">${this._shipping_lines_skeleton()}</div>
						</article>
						<article class="sfct-card" id="sfct-side-card">
							<div class="sfct-card-head" id="sfct-returned-head">
								<h2>${__("Returned Billings")}</h2>
								<p>${__("YTD returns that need follow-up")}</p>
							</div>
							<div id="sfct-returned" class="sfct-returned">
								<div class="sfct-returned-value">—</div>
								<div class="sfct-returned-meta">${__("Loading…")}</div>
							</div>
							<div class="sfct-card-head sfct-card-head-tight" id="sfct-modules-head">
								<h2>${__("Module snapshot")}</h2>
							</div>
							<div id="sfct-modules"></div>
							<div class="sfct-card-head sfct-card-head-tight" id="sfct-links-head">
								<h2>${__("Quick links")}</h2>
							</div>
							<div class="sfct-links" id="sfct-links"></div>
						</article>
					</section>

					<footer class="sfct-foot"><span id="sfct-asof"></span></footer>
				</div>
				<style>
					.sfct {
						--sfct-ink: var(--text-color, #111827);
						--sfct-muted: var(--text-muted, #6b7280);
						--sfct-line: var(--border-color, #e5e7eb);
						--sfct-surface: var(--fg-color, #ffffff);
						--sfct-soft: var(--subtle-fg, #f3f4f6);
						--sfct-accent: #2563eb;
						--sfct-warn: #d97706;
						--sfct-teal: #0d9488;
						--sfct-radius: 14px;
						width: 100%;
						margin-left: auto;
						margin-right: auto;
						padding: 0 var(--padding-md, 15px) 28px;
						color: var(--sfct-ink);
						box-sizing: border-box;
					}
					/* Match Frappe form full-width toggle (body.full-width / localStorage). */
					body:not(.full-width) .sfct {
						max-width: var(--page-max-width, 900px);
					}
					.sfct-filters-card {
						background: var(--sfct-surface);
						border: 1px solid var(--sfct-line);
						border-radius: var(--sfct-radius);
						padding: 16px 16px 8px;
						margin-bottom: 16px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
					}
					.sfct-section-title {
						font-size: 0.72rem;
						font-weight: 700;
						letter-spacing: 0.08em;
						text-transform: uppercase;
						color: var(--sfct-muted);
					}
					.sfct-filters-toolbar {
						display: flex;
						align-items: center;
						justify-content: space-between;
						gap: 12px;
						margin-bottom: 10px;
					}
					.sfct-filters-toolbar .sfct-filters-sub {
						margin: 0;
						flex: 1;
						min-width: 0;
					}
					.sfct-filters-sub,
					.sfct-section-sub {
						margin: 0 0 10px;
						font-size: 0.84rem;
						color: var(--sfct-muted);
					}
					.sfct-section-head {
						margin-bottom: 10px;
					}
					.sfct-filters-grid {
						display: grid;
						grid-template-columns: repeat(8, minmax(0, 1fr));
						gap: 10px 12px;
						align-items: end;
					}
					.sfct-filter-cell .form-group { margin-bottom: 8px; }
					.sfct-filter-cell .clearfix,
					.sfct-filter-cell .help-box { display: none !important; }
					.sfct-filter-cell .control-label {
						font-size: 0.72rem !important;
						font-weight: 600 !important;
						color: var(--sfct-muted) !important;
						margin-bottom: 4px !important;
					}
					.sfct-filter-cell input.input-with-feedback,
					.sfct-filter-cell .form-control {
						border-radius: 10px !important;
						min-height: 36px !important;
						border-color: var(--sfct-line) !important;
						background: var(--sfct-soft) !important;
					}

					.sfct-kpi-row {
						display: grid;
						grid-template-columns: repeat(4, minmax(0, 1fr));
						gap: 12px;
						margin-bottom: 16px;
					}
					.sfct-kpi-row.is-cols-1 { grid-template-columns: minmax(0, 1fr); }
					.sfct-kpi-row.is-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
					.sfct-kpi-row.is-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
					.sfct-kpi {
						position: relative;
						background: var(--sfct-surface);
						border: 1px solid var(--sfct-line);
						border-radius: var(--sfct-radius);
						padding: 18px 16px 16px;
						min-height: 118px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
						overflow: hidden;
					}
					.sfct-kpi::before {
						content: "";
						position: absolute;
						inset: 0 auto 0 0;
						width: 3px;
						background: var(--sfct-accent);
					}
					.sfct-kpi.is-warn::before { background: var(--sfct-warn); }
					.sfct-kpi.is-teal::before { background: var(--sfct-teal); }
					.sfct-kpi-label {
						margin: 0 0 12px;
						font-size: 0.72rem;
						font-weight: 700;
						letter-spacing: 0.05em;
						text-transform: uppercase;
						color: var(--sfct-muted);
					}
					.sfct-kpi-value {
						margin: 0 0 6px;
						font-size: 2rem;
						font-weight: 750;
						letter-spacing: -0.04em;
						line-height: 1;
					}
					.sfct-kpi-hint {
						margin: 0;
						font-size: 0.8rem;
						color: var(--sfct-muted);
					}
					.sfct-kpi.is-skeleton .sfct-kpi-value,
					.sfct-kpi.is-skeleton .sfct-kpi-hint {
						color: transparent;
						background: var(--sfct-soft);
						border-radius: 6px;
					}

					.sfct-panels {
						display: grid;
						grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
						gap: 12px;
					}
					.sfct-card {
						background: var(--sfct-surface);
						border: 1px solid var(--sfct-line);
						border-radius: var(--sfct-radius);
						padding: 18px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
					}
					.sfct-card-head h2 {
						margin: 0 0 2px;
						font-size: 1.05rem;
						font-weight: 700;
						letter-spacing: -0.02em;
					}
					.sfct-card-head p {
						margin: 0 0 14px;
						font-size: 0.84rem;
						color: var(--sfct-muted);
					}
					.sfct-card-head-tight {
						margin-top: 16px;
						padding-top: 14px;
						border-top: 1px solid var(--sfct-line);
					}
					.sfct-card-head-tight h2 { margin-bottom: 10px; }
					.sfct-card-head-tight p { display: none; }

					.sfct-settings-btn {
						flex: 0 0 auto;
						display: inline-flex;
						align-items: center;
						justify-content: center;
						width: 32px;
						height: 32px;
						margin: 0;
						padding: 0;
						border: 1px solid var(--sfct-line);
						border-radius: 10px;
						background: var(--sfct-soft);
						color: var(--sfct-muted);
						cursor: pointer;
						transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
					}
					.sfct-settings-btn:hover {
						color: var(--sfct-accent);
						border-color: var(--sfct-accent);
						background: #eff6ff;
					}

					.sfct-carrier {
						display: grid;
						grid-template-columns: minmax(0, 1fr) auto;
						gap: 4px 12px;
						margin-bottom: 12px;
					}
					.sfct-carrier-name {
						font-weight: 600;
						font-size: 0.92rem;
						overflow: hidden;
						text-overflow: ellipsis;
						white-space: nowrap;
					}
					.sfct-carrier-val {
						font-weight: 700;
						color: var(--sfct-accent);
					}
					.sfct-carrier-track {
						grid-column: 1 / -1;
						height: 8px;
						border-radius: 999px;
						background: var(--sfct-soft);
						overflow: hidden;
					}
					.sfct-carrier-fill {
						height: 100%;
						border-radius: inherit;
						background: var(--sfct-accent);
					}
					.sfct-empty {
						padding: 12px 0;
						color: var(--sfct-muted);
						font-size: 0.88rem;
					}
					.sfct-returned {
						padding: 16px;
						border-radius: 12px;
						background: var(--sfct-soft);
						border: 1px solid var(--sfct-line);
					}
					.sfct-returned-value {
						font-size: 2.2rem;
						font-weight: 750;
						letter-spacing: -0.04em;
						line-height: 1;
					}
					.sfct-returned-meta {
						margin-top: 6px;
						font-size: 0.82rem;
						color: var(--sfct-muted);
					}
					.sfct-mod-row {
						display: grid;
						grid-template-columns: minmax(0, 1.2fr) repeat(3, minmax(0, 0.7fr));
						gap: 8px;
						font-size: 0.8rem;
						padding: 10px 2px;
						border-bottom: 1px solid var(--sfct-line);
					}
					.sfct-mod-row:last-child { border-bottom: 0; }
					.sfct-mod-row span { color: var(--sfct-muted); }
					.sfct-mod-head {
						font-size: 0.68rem;
						font-weight: 700;
						letter-spacing: 0.05em;
						text-transform: uppercase;
						color: var(--sfct-muted);
						border-bottom: 0;
						padding-top: 0;
					}
					.sfct-links {
						display: flex;
						flex-wrap: wrap;
						gap: 8px;
						margin-top: 4px;
					}
					.sfct-foot {
						margin-top: 14px;
						font-size: 0.75rem;
						color: var(--sfct-muted);
					}
					.sfct-hidden { display: none !important; }
					@media (max-width: 1400px) {
						.sfct-filters-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
					}
					@media (max-width: 1200px) {
						.sfct-filters-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
					}
					@media (max-width: 1100px) {
						.sfct-kpi-row,
						.sfct-kpi-row.is-cols-3,
						.sfct-kpi-row.is-cols-4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
						.sfct-panels { grid-template-columns: 1fr; }
					}
					@media (max-width: 640px) {
						.sfct-filters-grid,
						.sfct-kpi-row,
						.sfct-kpi-row.is-cols-2,
						.sfct-kpi-row.is-cols-3,
						.sfct-kpi-row.is-cols-4 { grid-template-columns: 1fr; }
						.sfct-mod-row { grid-template-columns: 1fr 1fr; }
						.sfct-mod-head { display: none; }
					}
				</style>
			`);
			this.page.main.empty().append($ui);
			this.$root = this.page.main.find(".sfct");
		}

		mount_filters() {
			const $host = this.page.main.find("#sfct-filters");
			const self = this;

			FILTER_DEFS.forEach((def) => {
				const $cell = $('<div class="sfct-filter-cell">').appendTo($host);
				const df = {
					fieldtype: "Link",
					fieldname: def.key,
					label: def.label,
					options: def.options,
					onchange() {
						if (self._booting) return;
						if (def.key === "company") {
							self._clear_company_dependents();
						}
						self._schedule_refresh();
					},
				};
				if (def.company_scoped) {
					df.get_query = () => {
						const filters = Object.assign({}, def.extra_filters || {});
						const company = self._get("company");
						if (company) {
							const field =
								def.company_field ||
								(frappe.meta.has_field(def.options, "company")
									? "company"
									: frappe.meta.has_field(def.options, "custom_company")
										? "custom_company"
										: null);
							if (field) {
								filters[field] = company;
							}
						}
						return { filters };
					};
				}
				const ctrl = frappe.ui.form.make_control({
					df: df,
					parent: $cell,
					render_input: true,
				});
				ctrl.refresh();
				this.controls[def.key] = ctrl;
			});

			const $year = $('<div class="sfct-filter-cell">').appendTo($host);
			const year_ctrl = frappe.ui.form.make_control({
				df: {
					fieldtype: "Int",
					fieldname: "fiscal_year",
					label: __("Fiscal Year"),
					default: new Date().getFullYear(),
					onchange() {
						if (self._booting) return;
						self._sync_dates_from_fiscal_year();
						self._schedule_refresh();
					},
				},
				parent: $year,
				render_input: true,
			});
			year_ctrl.refresh();
			this.controls.fiscal_year = year_ctrl;

			const year = new Date().getFullYear();
			const $from = $('<div class="sfct-filter-cell">').appendTo($host);
			const from_ctrl = frappe.ui.form.make_control({
				df: {
					fieldtype: "Date",
					fieldname: "from_date",
					label: __("From Date"),
					default: year + "-01-01",
					reqd: 1,
					onchange() {
						if (self._booting) return;
						self._schedule_refresh();
					},
				},
				parent: $from,
				render_input: true,
			});
			from_ctrl.refresh();
			this.controls.from_date = from_ctrl;

			const $to = $('<div class="sfct-filter-cell">').appendTo($host);
			const to_ctrl = frappe.ui.form.make_control({
				df: {
					fieldtype: "Date",
					fieldname: "to_date",
					label: __("To Date"),
					default: frappe.datetime.get_today(),
					reqd: 1,
					onchange() {
						if (self._booting) return;
						self._schedule_refresh();
					},
				},
				parent: $to,
				render_input: true,
			});
			to_ctrl.refresh();
			this.controls.to_date = to_ctrl;
		}

		_sync_dates_from_fiscal_year() {
			const year = cint(this._get("fiscal_year")) || new Date().getFullYear();
			const from_date = year + "-01-01";
			const today = frappe.datetime.get_today();
			const year_end = year + "-12-31";
			const to_date = String(today).slice(0, 4) === String(year) ? today : year_end;
			this._set("from_date", from_date);
			this._set("to_date", to_date);
		}

		bind_settings() {
			this.$root.on("click", "[data-sfct-settings]", (e) => {
				e.preventDefault();
				this.open_settings();
			});
		}

		bind_full_width() {
			this._sync_full_width();
			if (!window._logistics_sfct_fullwidth_bound) {
				window._logistics_sfct_fullwidth_bound = true;
				$(document.body).on("toggleFullWidth.sfct", () => {
					const page = logistics.sea_freight_control_tower.page;
					if (page && page._sync_full_width) {
						page._sync_full_width();
					}
				});
			}
		}

		_sync_full_width() {
			// Mirror frappe.ui.toolbar full-width preference for optional CSS hooks.
			// Width itself is driven by body.full-width (see CSS above).
			let full_width = false;
			try {
				full_width =
					document.body.classList.contains("full-width") ||
					JSON.parse(localStorage.container_fullwidth || "false");
			} catch (e) {
				full_width = document.body.classList.contains("full-width");
			}
			if (this.$root && this.$root.length) {
				this.$root.toggleClass("is-page-full-width", !!full_width);
			}
		}

		_get(key) {
			const ctrl = this.controls[key];
			if (!ctrl || !ctrl.get_value) return "";
			const value = ctrl.get_value();
			return value == null ? "" : value;
		}

		_set(key, value) {
			const ctrl = this.controls[key];
			if (ctrl && ctrl.set_value) {
				ctrl.set_value(value || "");
			}
		}

		_clear_company_dependents() {
			["branch", "cost_center", "profit_center"].forEach((key) => this._set(key, ""));
		}

		_kpi_skeleton() {
			return [
				__("Open Job Files"),
				__("Avg Age of Open Jobs"),
				__("Job Files Handled"),
				__("Avg Lead Time / Milestone"),
			]
				.map(
					(label) => `
				<div class="sfct-kpi is-skeleton">
					<p class="sfct-kpi-label">${label}</p>
					<p class="sfct-kpi-value">000</p>
					<p class="sfct-kpi-hint">${__("Loading")}</p>
				</div>`
				)
				.join("");
		}

		_shipping_lines_skeleton() {
			return `<div class="sfct-empty">${__("Loading shipping line ranking…")}</div>`;
		}

		_schedule_refresh() {
			if (this._booting) return;
			if (this._refresh_timer) clearTimeout(this._refresh_timer);
			this._refresh_timer = setTimeout(() => this.refresh(), 200);
		}

		_bootstrap() {
			frappe.call({
				method: "logistics.sea_freight.sea_freight_control_tower.get_preferences",
				callback: (pr) => {
					this.prefs = deep_merge_prefs(pr.message);
					this._update_shipping_lines_title();
					frappe.call({
						method: "logistics.sea_freight.sea_freight_control_tower.get_filter_defaults",
						callback: (r) => {
							const data = r.message || {};
							if (data.company) this._set("company", data.company);
							if (data.fiscal_year) this._set("fiscal_year", data.fiscal_year);
							if (data.from_date) this._set("from_date", data.from_date);
							if (data.to_date) this._set("to_date", data.to_date);
							this._booting = false;
							this.refresh();
						},
						error: () => {
							const company = frappe.defaults.get_user_default("Company");
							if (company) this._set("company", company);
							this._sync_dates_from_fiscal_year();
							this._booting = false;
							this.refresh();
						},
					});
				},
				error: () => {
					this.prefs = deep_merge_prefs();
					this._booting = false;
					this.refresh();
				},
			});
		}

		_filters() {
			const year = this._get("fiscal_year") || new Date().getFullYear();
			let from_date = this._get("from_date");
			let to_date = this._get("to_date");
			if (!from_date || !to_date) {
				from_date = year + "-01-01";
				to_date = frappe.datetime.get_today();
			}
			return {
				company: this._get("company"),
				branch: this._get("branch"),
				cost_center: this._get("cost_center"),
				profit_center: this._get("profit_center"),
				unloco: this._get("unloco"),
				fiscal_year: year,
				from_date: from_date,
				to_date: to_date,
			};
		}

		_filter_summary(filters) {
			const parts = [];
			["company", "branch", "cost_center", "profit_center", "unloco"].forEach((key) => {
				if (filters[key]) parts.push(filters[key]);
			});
			if (filters.from_date || filters.to_date) {
				parts.push(
					__("{0} → {1}", [
						filters.from_date ? frappe.datetime.str_to_user(filters.from_date) : "…",
						filters.to_date ? frappe.datetime.str_to_user(filters.to_date) : "…",
					])
				);
			}
			return parts.join(" · ") || __("All companies");
		}

		_update_shipping_lines_title() {
			const limit = cint(this.prefs.shipping_lines.limit) || 10;
			this.page.main
				.find("#sfct-shipping_lines-title")
				.text(__("Top {0} Shipping Lines", [limit]));
		}

		save_prefs(next, opts) {
			opts = opts || {};
			const merged = deep_merge_prefs($.extend(true, {}, this.prefs, next || {}));
			frappe.call({
				method: "logistics.sea_freight.sea_freight_control_tower.save_preferences",
				args: { preferences: merged },
				callback: (r) => {
					this.prefs = deep_merge_prefs(r.message || merged);
					this._update_shipping_lines_title();
					if (opts.refresh !== false) {
						this.refresh();
					} else {
						this._apply_visibility();
						if (this._last_data) {
							this.render(this._last_data, this._last_filters);
						}
					}
					frappe.show_alert({ message: __("Preferences saved"), indicator: "green" });
				},
			});
		}

		open_settings() {
			const k = this.prefs.kpis;
			const d = new frappe.ui.Dialog({
				title: __("Control Tower Preferences"),
				fields: [
					{
						fieldtype: "Section Break",
						label: __("Key metrics"),
					},
					{
						fieldtype: "Check",
						fieldname: "show_open_jobs",
						label: __("Show Open Job Files"),
						default: cint(k.show_open_jobs),
					},
					{
						fieldtype: "Check",
						fieldname: "show_avg_age",
						label: __("Show Avg Age of Open Jobs"),
						default: cint(k.show_avg_age),
					},
					{
						fieldtype: "Check",
						fieldname: "show_handled",
						label: __("Show Job Files Handled"),
						default: cint(k.show_handled),
					},
					{
						fieldtype: "Check",
						fieldname: "show_lead_time",
						label: __("Show Avg Lead Time / Milestone"),
						default: cint(k.show_lead_time),
					},
					{
						fieldtype: "Int",
						fieldname: "warn_age_days",
						label: __("Warn when avg age exceeds (days)"),
						description: __("Highlight Avg Age in amber when over this threshold. Use 0 to disable."),
						default: cint(k.warn_age_days),
					},
					{
						fieldtype: "Section Break",
						label: __("Top Shipping Lines"),
					},
					{
						fieldtype: "Int",
						fieldname: "shipping_line_limit",
						label: __("Number of shipping lines to show"),
						description: __("Between 1 and 50. Ranking is by shipment count for the selected date range."),
						default: cint(this.prefs.shipping_lines.limit) || 10,
						reqd: 1,
					},
					{
						fieldtype: "Section Break",
						label: __("Side panels"),
					},
					{
						fieldtype: "Check",
						fieldname: "show_returned",
						label: __("Show Returned Billings"),
						default: cint(this.prefs.returned.visible),
					},
					{
						fieldtype: "Check",
						fieldname: "show_modules",
						label: __("Show Module snapshot"),
						default: cint(this.prefs.modules.visible),
					},
					{
						fieldtype: "Check",
						fieldname: "show_links",
						label: __("Show Quick links"),
						default: cint(this.prefs.links.visible),
					},
				],
				primary_action_label: __("Save"),
				primary_action: (values) => {
					this.save_prefs({
						kpis: {
							show_open_jobs: cint(values.show_open_jobs),
							show_avg_age: cint(values.show_avg_age),
							show_handled: cint(values.show_handled),
							show_lead_time: cint(values.show_lead_time),
							warn_age_days: cint(values.warn_age_days),
						},
						shipping_lines: {
							limit: Math.max(1, Math.min(50, cint(values.shipping_line_limit) || 10)),
						},
						returned: { visible: cint(values.show_returned) },
						modules: { visible: cint(values.show_modules) },
						links: { visible: cint(values.show_links) },
					});
					d.hide();
				},
			});
			d.show();
		}

		refresh() {
			const filters = this._filters();
			frappe.call({
				method: "logistics.sea_freight.sea_freight_control_tower.get_dashboard_data",
				args: Object.assign({}, filters, {
					shipping_line_limit: cint(this.prefs.shipping_lines.limit) || 10,
				}),
				callback: (r) => this.render(r.message || {}, filters),
				error: () => {
					frappe.show_alert({
						message: __("Could not load Sea Freight Control Tower data"),
						indicator: "red",
					});
				},
			});
		}

		_apply_visibility() {
			const showReturned = cint(this.prefs.returned.visible);
			const showModules = cint(this.prefs.modules.visible);
			const showLinks = cint(this.prefs.links.visible);
			this.page.main.find("#sfct-returned-head, #sfct-returned").toggleClass("sfct-hidden", !showReturned);
			this.page.main.find("#sfct-modules-head, #sfct-modules").toggleClass("sfct-hidden", !showModules);
			this.page.main.find("#sfct-links-head, #sfct-links").toggleClass("sfct-hidden", !showLinks);
		}

		render(data, filters) {
			filters = filters || data.filters || this._filters();
			if (data.preferences) {
				this.prefs = deep_merge_prefs(data.preferences);
			}
			if (data.shipping_line_limit) {
				this.prefs.shipping_lines.limit = cint(data.shipping_line_limit);
			}
			this._last_data = data;
			this._last_filters = filters;
			this._update_shipping_lines_title();
			this._apply_visibility();
			this._render_kpis(data.kpis || {});
			this._render_shipping_lines(data.top_shipping_lines || [], data.top_shipping_lines_max || 1);
			this._render_returned(data.kpis || {}, filters);
			this._render_modules(data.by_module || []);
			this._render_links(data.links || {});
			const asOf = data.as_of || "";
			this.page.main.find("#sfct-asof").text(
				asOf
					? __("As of {0} · {1}", [
							frappe.datetime.str_to_user(asOf),
							this._filter_summary(filters),
					  ])
					: ""
			);
		}

		_render_kpis(kpis) {
			const warnDays = cint(this.prefs.kpis.warn_age_days);
			const avgAge = flt(kpis.avg_age_open_jobs);
			const cards = [
				{
					key: "show_open_jobs",
					label: __("Open Job Files"),
					value: kpis.open_job_files_count,
					hint: __("Active sea job files"),
					cls: "",
					format: (v) => this._fmt_int(v),
				},
				{
					key: "show_avg_age",
					label: __("Avg Age of Open Jobs"),
					value: avgAge,
					hint: __("Days since booking"),
					cls: warnDays > 0 && avgAge > warnDays ? "is-warn" : "",
					format: (v) => this._fmt_days(v),
				},
				{
					key: "show_handled",
					label: __("Job Files Handled"),
					value: kpis.jobs_handled_count,
					hint: __("In selected date range"),
					cls: "is-teal",
					format: (v) => this._fmt_int(v),
				},
				{
					key: "show_lead_time",
					label: __("Avg Lead Time / Milestone"),
					value: kpis.avg_lead_time_per_milestone,
					hint: __("Actual vs planned (days)"),
					cls: "",
					format: (v) => this._fmt_days(v),
				},
			].filter((c) => cint(this.prefs.kpis[c.key]));

			const $row = this.page.main.find("#sfct-kpis");
			$row.removeClass("is-cols-1 is-cols-2 is-cols-3 is-cols-4");
			if (cards.length && cards.length < 4) {
				$row.addClass("is-cols-" + cards.length);
			}

			if (!cards.length) {
				$row.html(
					`<div class="sfct-empty">${__("No KPI cards enabled. Use settings to show metrics.")}</div>`
				);
				return;
			}

			$row.html(
				cards
					.map(
						(c) => `
					<div class="sfct-kpi ${c.cls}">
						<p class="sfct-kpi-label">${c.label}</p>
						<p class="sfct-kpi-value">${c.format(c.value)}</p>
						<p class="sfct-kpi-hint">${c.hint}</p>
					</div>`
					)
					.join("")
			);
		}

		_render_shipping_lines(rows, maxVal) {
			const $host = this.page.main.find("#sfct-shipping_lines");
			if (!rows.length) {
				$host.html(`<div class="sfct-empty">${__("No shipping line shipments found for this period.")}</div>`);
				return;
			}
			$host.html(
				rows
					.map((row, idx) => {
						const pct = Math.max(4, Math.round((flt(row.value) / maxVal) * 100));
						return `
						<div class="sfct-carrier">
							<div class="sfct-carrier-name">${idx + 1}. ${frappe.utils.escape_html(row.label || "")}</div>
							<div class="sfct-carrier-val">${this._fmt_int(row.value)}</div>
							<div class="sfct-carrier-track"><div class="sfct-carrier-fill" style="width:${pct}%"></div></div>
						</div>`;
					})
					.join("")
			);
		}

		_render_returned(kpis, filters) {
			filters = filters || {};
			const range =
				filters.from_date && filters.to_date
					? __("{0} → {1}", [
							frappe.datetime.str_to_user(filters.from_date),
							frappe.datetime.str_to_user(filters.to_date),
					  ])
					: filters.fiscal_year || "";
			this.page.main.find("#sfct-returned").html(`
				<div class="sfct-returned-value">${this._fmt_int(kpis.returned_billings_count || 0)}</div>
				<div class="sfct-returned-meta">${__("Returned billings · {0}", [range])}</div>
			`);
		}

		_render_modules(rows) {
			const $host = this.page.main.find("#sfct-modules");
			if (!rows.length) {
				$host.html(`<div class="sfct-empty">${__("No module breakdown available.")}</div>`);
				return;
			}
			$host.html(
				`
				<div class="sfct-mod-row sfct-mod-head">
					<span>${__("Module")}</span><span>${__("Open")}</span>
					<span>${__("Avg age")}</span><span>${__("Handled")}</span>
				</div>` +
					rows
						.map(
							(r) => `
					<div class="sfct-mod-row">
						<strong>${frappe.utils.escape_html(r.module || "")}</strong>
						<span>${this._fmt_int(r.open)}</span>
						<span>${this._fmt_days(r.open_avg_age)}</span>
						<span>${this._fmt_int(r.handled)}</span>
					</div>`
						)
						.join("")
			);
		}

		_render_links(links) {
			const filters = this._last_filters || this._filters();
			const airlineLimit = cint(this.prefs.shipping_lines.limit) || 10;
			const items = [
				{
					label: __("Open Job Files"),
					report: links.job_files_open || "SFCT Job Files Detail",
					extra: { scope: "Open" },
				},
				{
					label: __("Jobs Handled"),
					report: links.job_files_handled || "SFCT Job Files Detail",
					extra: { scope: "Handled" },
				},
				{
					label: __("Milestone Lead Time"),
					report: links.milestone_lead_time || "SFCT Milestone Lead Time",
					extra: {},
				},
				{
					label: __("Shipping Line Volumes"),
					report: links.shipping_line_volumes || "SFCT Shipping Line Volumes",
					extra: { limit: airlineLimit },
				},
				{
					label: __("Returned Billings"),
					report: links.returned_billings || "SFCT Returned Billings",
					extra: {},
				},
			];
			this.page.main.find("#sfct-links").html(
				items
					.map((i) => {
						const route = this._report_route(i.report, filters, i.extra);
						return `<a class="btn btn-default btn-xs" href="${route}">${i.label}</a>`;
					})
					.join("")
			);
		}

		_report_route(report_name, filters, extra) {
			const params = [];
			const merged = Object.assign({}, filters || {}, extra || {});
			["company", "branch", "cost_center", "profit_center", "unloco", "fiscal_year", "from_date", "to_date", "scope", "limit"].forEach(
				(key) => {
					const val = merged[key];
					if (val === undefined || val === null || val === "") return;
					params.push(
						encodeURIComponent(key) + "=" + encodeURIComponent(String(val))
					);
				}
			);
			const qs = params.length ? "?" + params.join("&") : "";
			return `/app/query-report/${encodeURIComponent(report_name)}${qs}`;
		}

		_fmt_int(v) {
			const n = cint(v);
			try {
				return n.toLocaleString();
			} catch (e) {
				return String(n);
			}
		}

		_fmt_days(v) {
			const n = flt(v);
			const s = n % 1 === 0 ? String(n) : n.toFixed(1);
			return __("{0} d", [s]);
		}
	}

	logistics.sea_freight_control_tower.SeaFreightControlTowerPage = SeaFreightControlTowerPage;

	function boot(wrapper) {
		if (logistics.sea_freight_control_tower.page) {
			return;
		}
		logistics.sea_freight_control_tower.page = new SeaFreightControlTowerPage(wrapper);
	}

	frappe.pages["sea-freight-control-tower"].on_page_load = function (wrapper) {
		boot(wrapper);
	};

	frappe.pages["sea-freight-control-tower"].on_page_show = function () {
		const page = logistics.sea_freight_control_tower.page;
		if (page && page.refresh) {
			page.refresh();
		}
	};
})();
