// route: air-freight-control-tower
// title: Air Freight Control Tower
// rev: 2026-07-24-native-page-fields

frappe.provide("logistics.air_freight_control_tower");

frappe.pages["air-freight-control-tower"].on_page_load = function (wrapper) {
	logistics.air_freight_control_tower.page = new logistics.air_freight_control_tower.AirFreightControlTowerPage(
		wrapper
	);
};

frappe.pages["air-freight-control-tower"].on_page_show = function () {
	const page = logistics.air_freight_control_tower.page;
	if (page && page.refresh) {
		page.refresh();
	}
};

(function () {
	class AirFreightControlTowerPage {
		constructor(wrapper) {
			this.wrapper = $(wrapper);
			this.page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Air Freight Control Tower"),
				single_column: true,
			});
			this.fields = {};
			this._refresh_timer = null;
			this._booting = true;
			this.setup_page_actions();
			this.setup_filters();
			this.make_layout();
			this._bootstrap();
		}

		setup_page_actions() {
			this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		}

		setup_filters() {
			const self = this;

			this.fields.company = this.page.add_field({
				fieldname: "company",
				label: __("Company"),
				fieldtype: "Link",
				options: "Company",
				default: frappe.defaults.get_user_default("Company"),
				change() {
					if (self._booting) return;
					self._clear_company_dependents();
					self._schedule_refresh();
				},
			});

			this.fields.branch = this.page.add_field({
				fieldname: "branch",
				label: __("Branch"),
				fieldtype: "Link",
				options: "Branch",
				get_query() {
					return self._company_query();
				},
				change() {
					self._schedule_refresh();
				},
			});

			this.fields.cost_center = this.page.add_field({
				fieldname: "cost_center",
				label: __("Cost Center"),
				fieldtype: "Link",
				options: "Cost Center",
				get_query() {
					return self._company_query({ is_group: 0 });
				},
				change() {
					self._schedule_refresh();
				},
			});

			this.fields.profit_center = this.page.add_field({
				fieldname: "profit_center",
				label: __("Profit Center"),
				fieldtype: "Link",
				options: "Profit Center",
				get_query() {
					return self._company_query();
				},
				change() {
					self._schedule_refresh();
				},
			});

			this.fields.unloco = this.page.add_field({
				fieldname: "unloco",
				label: __("UNLOCO"),
				fieldtype: "Link",
				options: "UNLOCO",
				change() {
					self._schedule_refresh();
				},
			});

			this.fields.fiscal_year = this.page.add_field({
				fieldname: "fiscal_year",
				label: __("Fiscal Year"),
				fieldtype: "Int",
				default: new Date().getFullYear(),
				change() {
					self._schedule_refresh();
				},
			});
		}

		_company_query(extra) {
			const filters = Object.assign({}, extra || {});
			const company = this._get("company");
			if (company) {
				filters.company = company;
			}
			return { filters };
		}

		_get(fieldname) {
			const field = this.fields[fieldname];
			if (!field) return "";
			const value = field.get_value ? field.get_value() : "";
			return value == null ? "" : value;
		}

		_set(fieldname, value) {
			const field = this.fields[fieldname];
			if (field && field.set_value) {
				field.set_value(value || "");
			}
		}

		_clear_company_dependents() {
			["branch", "cost_center", "profit_center"].forEach((key) => this._set(key, ""));
		}

		make_layout() {
			const $ui = $(`
				<div class="afct">
					<p class="afct-intro text-muted">
						${__("Open files, lead times, airline mix, and returned billings for air freight.")}
					</p>

					<section class="afct-kpi-row" id="afct-kpis" aria-live="polite">
						${this._kpi_skeleton()}
					</section>

					<section class="afct-panels">
						<article class="afct-panel">
							<div class="afct-panel-head">
								<h2>${__("Top 5 Airlines")}</h2>
								<p class="text-muted">${__("Shipments by airline for the selected year")}</p>
							</div>
							<div id="afct-airlines" class="afct-airlines">${this._airlines_skeleton()}</div>
						</article>
						<article class="afct-panel">
							<div class="afct-panel-head">
								<h2>${__("Returned Billings")}</h2>
								<p class="text-muted">${__("YTD returns that need follow-up")}</p>
							</div>
							<div id="afct-returned" class="afct-returned">
								<div class="afct-returned-value">—</div>
								<div class="afct-returned-meta text-muted">${__("Loading…")}</div>
							</div>
							<div class="afct-panel-head afct-panel-head-tight">
								<h2>${__("Module snapshot")}</h2>
							</div>
							<div id="afct-modules" class="afct-modules"></div>
							<div class="afct-links" id="afct-links"></div>
						</article>
					</section>

					<footer class="afct-foot text-muted">
						<span id="afct-asof"></span>
					</footer>
				</div>
				<style>
					.afct {
						padding: 4px 4px 24px;
					}
					.afct-intro {
						margin: 0 0 16px;
						font-size: 0.9rem;
					}
					.afct-kpi-row {
						display: grid;
						grid-template-columns: repeat(4, minmax(0, 1fr));
						gap: 12px;
						margin-bottom: 16px;
					}
					.afct-kpi {
						background: var(--fg-color, #fff);
						border: 1px solid var(--border-color, #e3e8ef);
						border-radius: 8px;
						padding: 14px 16px;
						min-height: 96px;
					}
					.afct-kpi-label {
						font-size: 0.72rem;
						font-weight: 600;
						color: var(--text-muted, #6c7685);
						text-transform: uppercase;
						letter-spacing: 0.04em;
						margin: 0 0 8px;
					}
					.afct-kpi-value {
						font-size: 1.75rem;
						font-weight: 600;
						line-height: 1.1;
						margin: 0 0 4px;
						color: var(--text-color, #1f272e);
					}
					.afct-kpi-hint {
						margin: 0;
						font-size: 0.78rem;
						color: var(--text-muted, #6c7685);
					}
					.afct-kpi.is-skeleton .afct-kpi-value,
					.afct-kpi.is-skeleton .afct-kpi-hint {
						background: var(--bg-color, #f3f3f3);
						color: transparent;
						border-radius: 4px;
					}
					.afct-panels {
						display: grid;
						grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
						gap: 12px;
					}
					.afct-panel {
						background: var(--fg-color, #fff);
						border: 1px solid var(--border-color, #e3e8ef);
						border-radius: 8px;
						padding: 16px;
					}
					.afct-panel-head h2 {
						font-size: 1rem;
						font-weight: 600;
						margin: 0 0 2px;
					}
					.afct-panel-head p {
						margin: 0 0 12px;
						font-size: 0.82rem;
					}
					.afct-panel-head-tight {
						margin-top: 16px;
						padding-top: 12px;
						border-top: 1px solid var(--border-color, #e3e8ef);
					}
					.afct-panel-head-tight h2 { margin-bottom: 10px; }
					.afct-airline {
						display: grid;
						grid-template-columns: minmax(0, 1fr) auto;
						gap: 4px 12px;
						align-items: center;
						margin-bottom: 10px;
					}
					.afct-airline-name {
						font-weight: 500;
						font-size: 0.9rem;
						min-width: 0;
						overflow: hidden;
						text-overflow: ellipsis;
						white-space: nowrap;
					}
					.afct-airline-val {
						font-weight: 600;
						font-size: 0.9rem;
					}
					.afct-airline-track {
						grid-column: 1 / -1;
						height: 6px;
						border-radius: 999px;
						background: var(--bg-color, #f0f2f5);
						overflow: hidden;
					}
					.afct-airline-fill {
						height: 100%;
						border-radius: inherit;
						background: var(--primary, #2490ef);
					}
					.afct-empty {
						padding: 12px 0;
						color: var(--text-muted, #6c7685);
						font-size: 0.88rem;
					}
					.afct-returned-value {
						font-size: 2rem;
						font-weight: 600;
						line-height: 1;
						color: var(--text-color, #1f272e);
					}
					.afct-returned-meta {
						margin-top: 6px;
						font-size: 0.82rem;
					}
					.afct-modules {
						display: flex;
						flex-direction: column;
						gap: 6px;
					}
					.afct-mod-row {
						display: grid;
						grid-template-columns: minmax(0, 1.2fr) repeat(3, minmax(0, 0.7fr));
						gap: 8px;
						font-size: 0.8rem;
						padding: 8px 0;
						border-bottom: 1px solid var(--border-color, #eef1f5);
					}
					.afct-mod-row:last-child { border-bottom: none; }
					.afct-mod-head {
						font-size: 0.68rem;
						text-transform: uppercase;
						letter-spacing: 0.04em;
						color: var(--text-muted, #6c7685);
						font-weight: 600;
						border-bottom: none;
						padding-top: 0;
						padding-bottom: 2px;
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
					}
					@media (max-width: 1100px) {
						.afct-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
						.afct-panels { grid-template-columns: 1fr; }
					}
					@media (max-width: 640px) {
						.afct-kpi-row { grid-template-columns: 1fr; }
						.afct-mod-row { grid-template-columns: 1fr 1fr; }
						.afct-mod-head { display: none; }
					}
				</style>
			`);
			this.page.main.empty().append($ui);
		}

		_kpi_skeleton() {
			const labels = [
				__("Open Job Files"),
				__("Avg Age of Open Jobs"),
				__("Job Files Handled"),
				__("Avg Lead Time / Milestone"),
			];
			return labels
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
					if (data.company) {
						this._set("company", data.company);
					}
					if (data.fiscal_year) {
						this._set("fiscal_year", data.fiscal_year);
					}
					this._booting = false;
					this.refresh();
				},
				error: () => {
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
				callback: (r) => {
					this.render(r.message || {}, filters);
				},
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
			const kpis = data.kpis || {};
			this._render_kpis(kpis);
			this._render_airlines(data.top_airlines || [], data.top_airlines_max || 1);
			this._render_returned(kpis, data.fiscal_year);
			this._render_modules(data.by_module || []);
			this._render_links(data.links || {});
			const asOf = data.as_of || "";
			this.wrapper.find("#afct-asof").text(
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
					format: (v) => this._fmt_int(v),
				},
				{
					label: __("Avg Age of Open Jobs"),
					value: kpis.avg_age_open_jobs,
					hint: __("Days since booking"),
					format: (v) => this._fmt_days(v),
				},
				{
					label: __("Job Files Handled"),
					value: kpis.jobs_handled_count,
					hint: __("Year to date"),
					format: (v) => this._fmt_int(v),
				},
				{
					label: __("Avg Lead Time / Milestone"),
					value: kpis.avg_lead_time_per_milestone,
					hint: __("Actual vs planned (days)"),
					format: (v) => this._fmt_days(v),
				},
			];
			const html = cards
				.map(
					(c) => `
				<div class="afct-kpi">
					<p class="afct-kpi-label">${c.label}</p>
					<p class="afct-kpi-value">${c.format(c.value)}</p>
					<p class="afct-kpi-hint">${c.hint}</p>
				</div>`
				)
				.join("");
			this.wrapper.find("#afct-kpis").html(html);
		}

		_render_airlines(rows, maxVal) {
			const $host = this.wrapper.find("#afct-airlines");
			if (!rows.length) {
				$host.html(`<div class="afct-empty">${__("No airline shipments found for this period.")}</div>`);
				return;
			}
			const html = rows
				.map((row, idx) => {
					const pct = Math.max(4, Math.round((flt(row.value) / maxVal) * 100));
					return `
					<div class="afct-airline">
						<div class="afct-airline-name">${idx + 1}. ${frappe.utils.escape_html(row.label || "")}</div>
						<div class="afct-airline-val">${this._fmt_int(row.value)}</div>
						<div class="afct-airline-track">
							<div class="afct-airline-fill" style="width:${pct}%"></div>
						</div>
					</div>`;
				})
				.join("");
			$host.html(html);
		}

		_render_returned(kpis, year) {
			const n = kpis.returned_billings_count || 0;
			this.wrapper.find("#afct-returned").html(`
				<div class="afct-returned-value">${this._fmt_int(n)}</div>
				<div class="afct-returned-meta text-muted">
					${__("Returned billings in FY {0}", [year || ""])}
				</div>
			`);
		}

		_render_modules(rows) {
			const $host = this.wrapper.find("#afct-modules");
			if (!rows.length) {
				$host.html(`<div class="afct-empty">${__("No module breakdown available.")}</div>`);
				return;
			}
			const head = `
				<div class="afct-mod-row afct-mod-head">
					<span>${__("Module")}</span>
					<span>${__("Open")}</span>
					<span>${__("Avg age")}</span>
					<span>${__("Handled")}</span>
				</div>`;
			const body = rows
				.map(
					(r) => `
				<div class="afct-mod-row">
					<strong>${frappe.utils.escape_html(r.module || "")}</strong>
					<span>${this._fmt_int(r.open)}</span>
					<span>${this._fmt_days(r.open_avg_age)}</span>
					<span>${this._fmt_int(r.handled)}</span>
				</div>`
				)
				.join("");
			$host.html(head + body);
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
			const html = items
				.map((i) => `<a class="btn btn-default btn-xs" href="${i.route}">${i.label}</a>`)
				.join("");
			this.wrapper.find("#afct-links").html(html);
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
})();
