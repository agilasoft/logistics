// Air Freight Control Tower — loaded via hooks page_js (cache-bustable asset)
// rev: 2026-07-24-hooks-make-control

frappe.provide("logistics.air_freight_control_tower");

(function () {
	if (logistics.air_freight_control_tower._hooks_loaded) {
		return;
	}
	logistics.air_freight_control_tower._hooks_loaded = true;

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

	class AirFreightControlTowerPage {
		constructor(wrapper) {
			this.wrapper = $(wrapper);
			this.page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Air Freight Control Tower"),
				single_column: true,
			});
			this.controls = {};
			this._refresh_timer = null;
			this._booting = true;
			this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
			this.make_layout();
			this.mount_filters();
			this._bootstrap();
		}

		make_layout() {
			const $ui = $(`
				<div class="afct">
					<section class="afct-filters-card">
						<div class="afct-filters-head">
							<div>
								<div class="afct-filters-kicker">${__("Parameters")}</div>
								<div class="afct-filters-sub">${__("Scope KPIs by company dimensions")}</div>
							</div>
						</div>
						<div class="afct-filters-grid" id="afct-filters"></div>
					</section>

					<section class="afct-kpi-row" id="afct-kpis" aria-live="polite">
						${this._kpi_skeleton()}
					</section>

					<section class="afct-panels">
						<article class="afct-card">
							<div class="afct-card-head">
								<h2>${__("Top 5 Airlines")}</h2>
								<p>${__("Shipments by airline for the selected year")}</p>
							</div>
							<div id="afct-airlines">${this._airlines_skeleton()}</div>
						</article>
						<article class="afct-card">
							<div class="afct-card-head">
								<h2>${__("Returned Billings")}</h2>
								<p>${__("YTD returns that need follow-up")}</p>
							</div>
							<div id="afct-returned" class="afct-returned">
								<div class="afct-returned-value">—</div>
								<div class="afct-returned-meta">${__("Loading…")}</div>
							</div>
							<div class="afct-card-head afct-card-head-tight">
								<h2>${__("Module snapshot")}</h2>
							</div>
							<div id="afct-modules"></div>
							<div class="afct-links" id="afct-links"></div>
						</article>
					</section>

					<footer class="afct-foot"><span id="afct-asof"></span></footer>
				</div>
				<style>
					.afct {
						--afct-ink: var(--text-color, #111827);
						--afct-muted: var(--text-muted, #6b7280);
						--afct-line: var(--border-color, #e5e7eb);
						--afct-surface: var(--fg-color, #ffffff);
						--afct-soft: var(--subtle-fg, #f3f4f6);
						--afct-accent: var(--primary, #2563eb);
						--afct-warn: #d97706;
						--afct-teal: #0d9488;
						--afct-radius: 14px;
						padding: 0 0 28px;
						color: var(--afct-ink);
					}
					.afct-filters-card {
						background: var(--afct-surface);
						border: 1px solid var(--afct-line);
						border-radius: var(--afct-radius);
						padding: 16px 16px 8px;
						margin-bottom: 16px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
					}
					.afct-filters-head { margin-bottom: 10px; }
					.afct-filters-kicker {
						font-size: 0.72rem;
						font-weight: 700;
						letter-spacing: 0.08em;
						text-transform: uppercase;
						color: var(--afct-muted);
					}
					.afct-filters-sub {
						margin-top: 2px;
						font-size: 0.84rem;
						color: var(--afct-muted);
					}
					.afct-filters-grid {
						display: grid;
						grid-template-columns: repeat(6, minmax(0, 1fr));
						gap: 10px 12px;
						align-items: end;
					}
					.afct-filter-cell .form-group { margin-bottom: 8px; }
					.afct-filter-cell .clearfix,
					.afct-filter-cell .help-box { display: none !important; }
					.afct-filter-cell .control-label {
						font-size: 0.72rem !important;
						font-weight: 600 !important;
						color: var(--afct-muted) !important;
						margin-bottom: 4px !important;
					}
					.afct-filter-cell input.input-with-feedback,
					.afct-filter-cell .form-control {
						border-radius: 10px !important;
						min-height: 36px !important;
						border-color: var(--afct-line) !important;
						background: var(--afct-soft) !important;
					}

					.afct-kpi-row {
						display: grid;
						grid-template-columns: repeat(4, minmax(0, 1fr));
						gap: 12px;
						margin-bottom: 16px;
					}
					.afct-kpi {
						position: relative;
						background: var(--afct-surface);
						border: 1px solid var(--afct-line);
						border-radius: var(--afct-radius);
						padding: 18px 16px 16px;
						min-height: 118px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
						overflow: hidden;
					}
					.afct-kpi::before {
						content: "";
						position: absolute;
						inset: 0 auto 0 0;
						width: 3px;
						background: var(--afct-accent);
					}
					.afct-kpi.is-warn::before { background: var(--afct-warn); }
					.afct-kpi.is-teal::before { background: var(--afct-teal); }
					.afct-kpi-label {
						margin: 0 0 12px;
						font-size: 0.72rem;
						font-weight: 700;
						letter-spacing: 0.05em;
						text-transform: uppercase;
						color: var(--afct-muted);
					}
					.afct-kpi-value {
						margin: 0 0 6px;
						font-size: 2rem;
						font-weight: 750;
						letter-spacing: -0.04em;
						line-height: 1;
					}
					.afct-kpi-hint {
						margin: 0;
						font-size: 0.8rem;
						color: var(--afct-muted);
					}
					.afct-kpi.is-skeleton .afct-kpi-value,
					.afct-kpi.is-skeleton .afct-kpi-hint {
						color: transparent;
						background: var(--afct-soft);
						border-radius: 6px;
					}

					.afct-panels {
						display: grid;
						grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
						gap: 12px;
					}
					.afct-card {
						background: var(--afct-surface);
						border: 1px solid var(--afct-line);
						border-radius: var(--afct-radius);
						padding: 18px;
						box-shadow: 0 8px 24px rgba(17, 24, 39, 0.04);
					}
					.afct-card-head h2 {
						margin: 0 0 2px;
						font-size: 1.05rem;
						font-weight: 700;
						letter-spacing: -0.02em;
					}
					.afct-card-head p {
						margin: 0 0 14px;
						font-size: 0.84rem;
						color: var(--afct-muted);
					}
					.afct-card-head-tight {
						margin-top: 16px;
						padding-top: 14px;
						border-top: 1px solid var(--afct-line);
					}
					.afct-card-head-tight h2 { margin-bottom: 10px; }
					.afct-card-head-tight p { display: none; }

					.afct-airline {
						display: grid;
						grid-template-columns: minmax(0, 1fr) auto;
						gap: 4px 12px;
						margin-bottom: 12px;
					}
					.afct-airline-name {
						font-weight: 600;
						font-size: 0.92rem;
						overflow: hidden;
						text-overflow: ellipsis;
						white-space: nowrap;
					}
					.afct-airline-val {
						font-weight: 700;
						color: var(--afct-accent);
					}
					.afct-airline-track {
						grid-column: 1 / -1;
						height: 8px;
						border-radius: 999px;
						background: var(--afct-soft);
						overflow: hidden;
					}
					.afct-airline-fill {
						height: 100%;
						border-radius: inherit;
						background: linear-gradient(90deg, var(--afct-accent), var(--afct-teal));
					}
					.afct-empty {
						padding: 12px 0;
						color: var(--afct-muted);
						font-size: 0.88rem;
					}
					.afct-returned {
						padding: 16px;
						border-radius: 12px;
						background: var(--afct-soft);
						border: 1px solid var(--afct-line);
					}
					.afct-returned-value {
						font-size: 2.2rem;
						font-weight: 750;
						letter-spacing: -0.04em;
						line-height: 1;
					}
					.afct-returned-meta {
						margin-top: 6px;
						font-size: 0.82rem;
						color: var(--afct-muted);
					}
					.afct-mod-row {
						display: grid;
						grid-template-columns: minmax(0, 1.2fr) repeat(3, minmax(0, 0.7fr));
						gap: 8px;
						font-size: 0.8rem;
						padding: 10px 2px;
						border-bottom: 1px solid var(--afct-line);
					}
					.afct-mod-row:last-child { border-bottom: 0; }
					.afct-mod-row span { color: var(--afct-muted); }
					.afct-mod-head {
						font-size: 0.68rem;
						font-weight: 700;
						letter-spacing: 0.05em;
						text-transform: uppercase;
						color: var(--afct-muted);
						border-bottom: 0;
						padding-top: 0;
					}
					.afct-links {
						display: flex;
						flex-wrap: wrap;
						gap: 8px;
						margin-top: 14px;
					}
					.afct-foot {
						margin-top: 14px;
						font-size: 0.75rem;
						color: var(--afct-muted);
					}
					@media (max-width: 1200px) {
						.afct-filters-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
					}
					@media (max-width: 1100px) {
						.afct-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
						.afct-panels { grid-template-columns: 1fr; }
					}
					@media (max-width: 640px) {
						.afct-filters-grid,
						.afct-kpi-row { grid-template-columns: 1fr; }
						.afct-mod-row { grid-template-columns: 1fr 1fr; }
						.afct-mod-head { display: none; }
					}
				</style>
			`);
			this.page.main.empty().append($ui);
		}

		mount_filters() {
			const $host = this.page.main.find("#afct-filters");
			const self = this;

			FILTER_DEFS.forEach((def) => {
				const $cell = $('<div class="afct-filter-cell">').appendTo($host);
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
						if (company) filters.company = company;
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

			const $year = $('<div class="afct-filter-cell">').appendTo($host);
			const year_ctrl = frappe.ui.form.make_control({
				df: {
					fieldtype: "Int",
					fieldname: "fiscal_year",
					label: __("Fiscal Year"),
					default: new Date().getFullYear(),
					onchange() {
						self._schedule_refresh();
					},
				},
				parent: $year,
				render_input: true,
			});
			year_ctrl.refresh();
			this.controls.fiscal_year = year_ctrl;
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
				<div class="afct-kpi is-skeleton">
					<p class="afct-kpi-label">${label}</p>
					<p class="afct-kpi-value">000</p>
					<p class="afct-kpi-hint">${__("Loading")}</p>
				</div>`
				)
				.join("");
		}

		_airlines_skeleton() {
			return `<div class="afct-empty">${__("Loading airline ranking…")}</div>`;
		}

		_schedule_refresh() {
			if (this._booting) return;
			if (this._refresh_timer) clearTimeout(this._refresh_timer);
			this._refresh_timer = setTimeout(() => this.refresh(), 200);
		}

		_bootstrap() {
			frappe.call({
				method: "logistics.air_freight.air_freight_control_tower.get_filter_defaults",
				callback: (r) => {
					const data = r.message || {};
					if (data.company) this._set("company", data.company);
					if (data.fiscal_year) this._set("fiscal_year", data.fiscal_year);
					this._booting = false;
					this.refresh();
				},
				error: () => {
					const company = frappe.defaults.get_user_default("Company");
					if (company) this._set("company", company);
					this._booting = false;
					this.refresh();
				},
			});
		}

		_filters() {
			return {
				company: this._get("company"),
				branch: this._get("branch"),
				cost_center: this._get("cost_center"),
				profit_center: this._get("profit_center"),
				unloco: this._get("unloco"),
				fiscal_year: this._get("fiscal_year") || new Date().getFullYear(),
			};
		}

		_filter_summary(filters) {
			const parts = [];
			["company", "branch", "cost_center", "profit_center", "unloco"].forEach((key) => {
				if (filters[key]) parts.push(filters[key]);
			});
			return parts.join(" · ") || __("All companies");
		}

		refresh() {
			const filters = this._filters();
			frappe.call({
				method: "logistics.air_freight.air_freight_control_tower.get_dashboard_data",
				args: filters,
				callback: (r) => this.render(r.message || {}, filters),
				error: () => {
					frappe.show_alert({
						message: __("Could not load Air Freight Control Tower data"),
						indicator: "red",
					});
				},
			});
		}

		render(data, filters) {
			filters = filters || data.filters || this._filters();
			this._render_kpis(data.kpis || {});
			this._render_airlines(data.top_airlines || [], data.top_airlines_max || 1);
			this._render_returned(data.kpis || {}, data.fiscal_year);
			this._render_modules(data.by_module || []);
			this._render_links(data.links || {});
			const asOf = data.as_of || "";
			this.page.main.find("#afct-asof").text(
				asOf
					? __("As of {0} · {1} · FY {2}", [
							frappe.datetime.str_to_user(asOf),
							this._filter_summary(filters),
							data.fiscal_year || filters.fiscal_year || "",
					  ])
					: ""
			);
		}

		_render_kpis(kpis) {
			const cards = [
				{
					label: __("Open Job Files"),
					value: kpis.open_job_files_count,
					hint: __("Active air job files"),
					cls: "",
					format: (v) => this._fmt_int(v),
				},
				{
					label: __("Avg Age of Open Jobs"),
					value: kpis.avg_age_open_jobs,
					hint: __("Days since booking"),
					cls: "is-warn",
					format: (v) => this._fmt_days(v),
				},
				{
					label: __("Job Files Handled"),
					value: kpis.jobs_handled_count,
					hint: __("Year to date"),
					cls: "is-teal",
					format: (v) => this._fmt_int(v),
				},
				{
					label: __("Avg Lead Time / Milestone"),
					value: kpis.avg_lead_time_per_milestone,
					hint: __("Actual vs planned (days)"),
					cls: "",
					format: (v) => this._fmt_days(v),
				},
			];
			this.page.main.find("#afct-kpis").html(
				cards
					.map(
						(c) => `
					<div class="afct-kpi ${c.cls}">
						<p class="afct-kpi-label">${c.label}</p>
						<p class="afct-kpi-value">${c.format(c.value)}</p>
						<p class="afct-kpi-hint">${c.hint}</p>
					</div>`
					)
					.join("")
			);
		}

		_render_airlines(rows, maxVal) {
			const $host = this.page.main.find("#afct-airlines");
			if (!rows.length) {
				$host.html(`<div class="afct-empty">${__("No airline shipments found for this period.")}</div>`);
				return;
			}
			$host.html(
				rows
					.map((row, idx) => {
						const pct = Math.max(4, Math.round((flt(row.value) / maxVal) * 100));
						return `
						<div class="afct-airline">
							<div class="afct-airline-name">${idx + 1}. ${frappe.utils.escape_html(row.label || "")}</div>
							<div class="afct-airline-val">${this._fmt_int(row.value)}</div>
							<div class="afct-airline-track"><div class="afct-airline-fill" style="width:${pct}%"></div></div>
						</div>`;
					})
					.join("")
			);
		}

		_render_returned(kpis, year) {
			this.page.main.find("#afct-returned").html(`
				<div class="afct-returned-value">${this._fmt_int(kpis.returned_billings_count || 0)}</div>
				<div class="afct-returned-meta">${__("Returned billings in FY {0}", [year || ""])}</div>
			`);
		}

		_render_modules(rows) {
			const $host = this.page.main.find("#afct-modules");
			if (!rows.length) {
				$host.html(`<div class="afct-empty">${__("No module breakdown available.")}</div>`);
				return;
			}
			$host.html(
				`
				<div class="afct-mod-row afct-mod-head">
					<span>${__("Module")}</span><span>${__("Open")}</span>
					<span>${__("Avg age")}</span><span>${__("Handled")}</span>
				</div>` +
					rows
						.map(
							(r) => `
					<div class="afct-mod-row">
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
			const items = [];
			if (links.control_tower_dashboard) {
				items.push({
					label: __("Open CT Dashboard"),
					route: `/app/dashboard-view/${encodeURIComponent(links.control_tower_dashboard)}`,
				});
			}
			if (links.jobs_report) {
				items.push({
					label: __("Jobs KPI Report"),
					route: `/app/query-report/${encodeURIComponent(links.jobs_report)}`,
				});
			}
			if (links.returned_billings_report) {
				items.push({
					label: __("Returned Billings"),
					route: `/app/query-report/${encodeURIComponent(links.returned_billings_report)}`,
				});
			}
			this.page.main.find("#afct-links").html(
				items.map((i) => `<a class="btn btn-default btn-xs" href="${i.route}">${i.label}</a>`).join("")
			);
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

	logistics.air_freight_control_tower.AirFreightControlTowerPage = AirFreightControlTowerPage;

	function boot(wrapper) {
		if (logistics.air_freight_control_tower.page) {
			return;
		}
		logistics.air_freight_control_tower.page = new AirFreightControlTowerPage(wrapper);
	}

	frappe.pages["air-freight-control-tower"].on_page_load = function (wrapper) {
		boot(wrapper);
	};

	frappe.pages["air-freight-control-tower"].on_page_show = function () {
		const page = logistics.air_freight_control_tower.page;
		if (page && page.refresh) {
			page.refresh();
		}
	};
})();
