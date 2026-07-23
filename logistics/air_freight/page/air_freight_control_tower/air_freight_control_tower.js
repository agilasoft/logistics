// route: air-freight-control-tower
// title: Air Freight Control Tower

frappe.provide("logistics.air_freight_control_tower");

frappe.pages["air-freight-control-tower"].on_page_load = function (wrapper) {
	logistics.air_freight_control_tower.page = new logistics.air_freight_control_tower.AirFreightControlTowerPage(
		wrapper
	);
};

(function () {
	const DEFAULT_ORG = "ATN Airfreight";

	class AirFreightControlTowerPage {
		constructor(wrapper) {
			this.wrapper = $(wrapper);
			this.page = frappe.ui.make_app_page({
				parent: wrapper,
				title: __("Air Freight Control Tower"),
				single_column: true,
			});
			this._orgs_loaded = false;
			this.make_layout();
			this.bind_events();
			this._load_organizations(() => this.refresh());
		}

		make_layout() {
			const year = new Date().getFullYear();
			const $ui = $(`
				<div class="afct">
					<header class="afct-hero">
						<div class="afct-hero-copy">
							<p class="afct-brand">${__("Air Freight Control Tower")}</p>
							<h1 class="afct-headline">${__("Operational pulse for air job files")}</h1>
							<p class="afct-lede">
								${__("Live view of open files, lead times, airline mix, and returned billings.")}
							</p>
						</div>
						<div class="afct-toolbar">
							<label class="afct-field">
								<span>${__("Organization")}</span>
								<select id="afct-org" class="form-control input-sm"></select>
							</label>
							<label class="afct-field afct-field-year">
								<span>${__("Fiscal Year")}</span>
								<input id="afct-year" type="number" class="form-control input-sm" value="${year}" min="2000" max="2100" />
							</label>
							<button type="button" class="btn btn-primary btn-sm afct-refresh" id="afct-refresh">
								<i class="fa fa-refresh"></i> ${__("Refresh")}
							</button>
						</div>
					</header>

					<section class="afct-kpi-row" id="afct-kpis" aria-live="polite">
						${this._kpi_skeleton()}
					</section>

					<section class="afct-panels">
						<article class="afct-panel afct-panel-airlines">
							<div class="afct-panel-head">
								<h2>${__("Top 5 Airlines")}</h2>
								<p>${__("Shipments by airline for the selected year")}</p>
							</div>
							<div id="afct-airlines" class="afct-airlines">${this._airlines_skeleton()}</div>
						</article>
						<article class="afct-panel afct-panel-side">
							<div class="afct-panel-head">
								<h2>${__("Returned Billings")}</h2>
								<p>${__("YTD returns that need follow-up")}</p>
							</div>
							<div id="afct-returned" class="afct-returned">
								<div class="afct-returned-value">—</div>
								<div class="afct-returned-meta">${__("Loading…")}</div>
							</div>
							<div class="afct-panel-head afct-panel-head-tight">
								<h2>${__("Module snapshot")}</h2>
							</div>
							<div id="afct-modules" class="afct-modules"></div>
							<div class="afct-links" id="afct-links"></div>
						</article>
					</section>

					<footer class="afct-foot">
						<span id="afct-asof"></span>
					</footer>
				</div>
				<style>
					@import url("https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=IBM+Plex+Sans:wght@400;500;600&display=swap");

					.afct {
						--afct-ink: #0b1f33;
						--afct-muted: #5a6f84;
						--afct-sky: #1483c8;
						--afct-sky-deep: #0b5f96;
						--afct-teal: #0f766e;
						--afct-warn: #c2410c;
						--afct-paper: #f3f7fb;
						--afct-line: rgba(11, 31, 51, 0.1);
						--afct-radius: 14px;
						padding: 0 4px 28px;
						font-family: "IBM Plex Sans", sans-serif;
						color: var(--afct-ink);
						animation: afct-fade-in 0.45s ease both;
					}
					.afct * { box-sizing: border-box; }
					@keyframes afct-fade-in {
						from { opacity: 0; transform: translateY(8px); }
						to { opacity: 1; transform: translateY(0); }
					}
					@keyframes afct-bar-grow {
						from { transform: scaleX(0); }
						to { transform: scaleX(1); }
					}
					@keyframes afct-pulse {
						0%, 100% { opacity: 0.45; }
						50% { opacity: 0.85; }
					}

					.afct-hero {
						display: flex;
						flex-wrap: wrap;
						justify-content: space-between;
						gap: 18px 28px;
						align-items: flex-end;
						padding: 22px 22px 20px;
						margin-bottom: 16px;
						border-radius: var(--afct-radius);
						background:
							radial-gradient(1200px 280px at 8% -20%, rgba(20, 131, 200, 0.28), transparent 55%),
							radial-gradient(900px 260px at 92% 0%, rgba(15, 118, 110, 0.18), transparent 50%),
							linear-gradient(145deg, #0b1f33 0%, #12324d 55%, #0f3a52 100%);
						color: #e8f2fa;
						overflow: hidden;
						position: relative;
					}
					.afct-hero::after {
						content: "";
						position: absolute;
						inset: auto -40px -60px auto;
						width: 220px;
						height: 220px;
						border-radius: 50%;
						border: 18px solid rgba(232, 242, 250, 0.06);
						pointer-events: none;
					}
					.afct-brand {
						font-family: Manrope, sans-serif;
						font-weight: 800;
						font-size: 1.35rem;
						letter-spacing: -0.02em;
						margin: 0 0 6px;
						line-height: 1.15;
					}
					.afct-headline {
						font-family: Manrope, sans-serif;
						font-weight: 600;
						font-size: 1.05rem;
						margin: 0 0 6px;
						color: rgba(232, 242, 250, 0.92);
					}
					.afct-lede {
						margin: 0;
						max-width: 36rem;
						font-size: 0.88rem;
						line-height: 1.45;
						color: rgba(232, 242, 250, 0.72);
					}
					.afct-toolbar {
						display: flex;
						flex-wrap: wrap;
						align-items: flex-end;
						gap: 10px;
						position: relative;
						z-index: 1;
					}
					.afct-field {
						display: flex;
						flex-direction: column;
						gap: 4px;
						margin: 0;
						min-width: 11rem;
					}
					.afct-field-year { min-width: 6.5rem; max-width: 7.5rem; }
					.afct-field span {
						font-size: 0.7rem;
						text-transform: uppercase;
						letter-spacing: 0.06em;
						color: rgba(232, 242, 250, 0.65);
						font-weight: 600;
					}
					.afct-field .form-control {
						border: 1px solid rgba(255,255,255,0.18);
						background: rgba(255,255,255,0.1);
						color: #fff;
						height: 32px;
						border-radius: 8px;
					}
					.afct-field .form-control option { color: #0b1f33; }
					.afct-refresh {
						height: 32px;
						border-radius: 8px;
						border: none;
						background: #e8f2fa !important;
						color: var(--afct-ink) !important;
						font-weight: 600;
					}
					.afct-refresh:hover { filter: brightness(0.96); }

					.afct-kpi-row {
						display: grid;
						grid-template-columns: repeat(4, minmax(0, 1fr));
						gap: 12px;
						margin-bottom: 14px;
					}
					.afct-kpi {
						background: var(--afct-paper);
						border: 1px solid var(--afct-line);
						border-radius: var(--afct-radius);
						padding: 16px 16px 14px;
						position: relative;
						overflow: hidden;
						animation: afct-fade-in 0.5s ease both;
						min-height: 110px;
					}
					.afct-kpi:nth-child(1) { animation-delay: 0.05s; }
					.afct-kpi:nth-child(2) { animation-delay: 0.1s; }
					.afct-kpi:nth-child(3) { animation-delay: 0.15s; }
					.afct-kpi:nth-child(4) { animation-delay: 0.2s; }
					.afct-kpi::before {
						content: "";
						position: absolute;
						left: 0; top: 0; bottom: 0;
						width: 3px;
						background: var(--afct-sky);
					}
					.afct-kpi-label {
						font-size: 0.75rem;
						font-weight: 600;
						color: var(--afct-muted);
						text-transform: uppercase;
						letter-spacing: 0.04em;
						margin: 0 0 10px;
					}
					.afct-kpi-value {
						font-family: Manrope, sans-serif;
						font-weight: 800;
						font-size: 2rem;
						letter-spacing: -0.03em;
						line-height: 1;
						margin: 0 0 6px;
						color: var(--afct-ink);
					}
					.afct-kpi-hint {
						margin: 0;
						font-size: 0.78rem;
						color: var(--afct-muted);
					}
					.afct-kpi.is-warn::before { background: var(--afct-warn); }
					.afct-kpi.is-teal::before { background: var(--afct-teal); }
					.afct-kpi.is-skeleton .afct-kpi-value,
					.afct-kpi.is-skeleton .afct-kpi-hint {
						background: rgba(11,31,51,0.08);
						color: transparent;
						border-radius: 6px;
						animation: afct-pulse 1.2s ease infinite;
					}

					.afct-panels {
						display: grid;
						grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
						gap: 12px;
					}
					.afct-panel {
						background: #fff;
						border: 1px solid var(--afct-line);
						border-radius: var(--afct-radius);
						padding: 18px;
						animation: afct-fade-in 0.55s ease both;
						animation-delay: 0.18s;
					}
					.afct-panel-head h2 {
						font-family: Manrope, sans-serif;
						font-size: 1.05rem;
						font-weight: 700;
						margin: 0 0 2px;
						letter-spacing: -0.01em;
					}
					.afct-panel-head p {
						margin: 0 0 14px;
						font-size: 0.82rem;
						color: var(--afct-muted);
					}
					.afct-panel-head-tight {
						margin-top: 18px;
						padding-top: 14px;
						border-top: 1px solid var(--afct-line);
					}
					.afct-panel-head-tight h2 { margin-bottom: 10px; }
					.afct-panel-head-tight p { display: none; }

					.afct-airline {
						display: grid;
						grid-template-columns: minmax(0, 1fr) auto;
						gap: 4px 12px;
						align-items: center;
						margin-bottom: 12px;
					}
					.afct-airline-name {
						font-weight: 600;
						font-size: 0.9rem;
						min-width: 0;
						overflow: hidden;
						text-overflow: ellipsis;
						white-space: nowrap;
					}
					.afct-airline-val {
						font-family: Manrope, sans-serif;
						font-weight: 700;
						font-size: 0.9rem;
						color: var(--afct-sky-deep);
					}
					.afct-airline-track {
						grid-column: 1 / -1;
						height: 8px;
						border-radius: 999px;
						background: rgba(20, 131, 200, 0.12);
						overflow: hidden;
					}
					.afct-airline-fill {
						height: 100%;
						border-radius: inherit;
						background: linear-gradient(90deg, var(--afct-sky), var(--afct-teal));
						transform-origin: left center;
						animation: afct-bar-grow 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
					}
					.afct-empty {
						padding: 18px 4px;
						color: var(--afct-muted);
						font-size: 0.88rem;
					}

					.afct-returned {
						padding: 16px;
						border-radius: 12px;
						background:
							linear-gradient(135deg, rgba(194, 65, 12, 0.08), rgba(194, 65, 12, 0.02));
						border: 1px solid rgba(194, 65, 12, 0.18);
					}
					.afct-returned-value {
						font-family: Manrope, sans-serif;
						font-weight: 800;
						font-size: 2.4rem;
						letter-spacing: -0.03em;
						color: var(--afct-warn);
						line-height: 1;
					}
					.afct-returned-meta {
						margin-top: 6px;
						font-size: 0.82rem;
						color: var(--afct-muted);
					}

					.afct-modules {
						display: flex;
						flex-direction: column;
						gap: 8px;
					}
					.afct-mod-row {
						display: grid;
						grid-template-columns: minmax(0, 1.2fr) repeat(3, minmax(0, 0.7fr));
						gap: 8px;
						font-size: 0.78rem;
						padding: 8px 10px;
						border-radius: 8px;
						background: var(--afct-paper);
					}
					.afct-mod-row strong { font-weight: 600; }
					.afct-mod-row span { color: var(--afct-muted); }
					.afct-mod-head {
						font-size: 0.68rem;
						text-transform: uppercase;
						letter-spacing: 0.05em;
						color: var(--afct-muted);
						font-weight: 600;
						background: transparent;
						padding-top: 0;
						padding-bottom: 2px;
					}

					.afct-links {
						display: flex;
						flex-wrap: wrap;
						gap: 8px;
						margin-top: 16px;
					}
					.afct-links a {
						font-size: 0.78rem;
						font-weight: 600;
						color: var(--afct-sky-deep);
						text-decoration: none;
						padding: 6px 10px;
						border-radius: 8px;
						border: 1px solid rgba(20, 131, 200, 0.25);
						background: rgba(20, 131, 200, 0.06);
					}
					.afct-links a:hover { background: rgba(20, 131, 200, 0.12); }

					.afct-foot {
						margin-top: 14px;
						font-size: 0.75rem;
						color: var(--afct-muted);
					}

					@media (max-width: 1100px) {
						.afct-kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
						.afct-panels { grid-template-columns: 1fr; }
					}
					@media (max-width: 640px) {
						.afct-kpi-row { grid-template-columns: 1fr; }
						.afct-hero { padding: 18px; }
						.afct-brand { font-size: 1.15rem; }
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

		bind_events() {
			this.wrapper.on("click", "#afct-refresh", () => this.refresh());
			this.wrapper.on("change", "#afct-org, #afct-year", () => this.refresh());
		}

		_load_organizations(done) {
			frappe.call({
				method: "logistics.air_freight.air_freight_control_tower.get_organizations",
				callback: (r) => {
					const data = r.message || {};
					const $sel = this.wrapper.find("#afct-org");
					$sel.empty();
					(data.organizations || []).forEach((o) => {
						const name = o.organization_name || o.name;
						$sel.append($("<option>").attr("value", name).text(name));
					});
					const def = data.default || DEFAULT_ORG;
					if ($sel.find(`option[value="${def}"]`).length) {
						$sel.val(def);
					}
					this._orgs_loaded = true;
					if (done) done();
				},
				error: () => {
					const $sel = this.wrapper.find("#afct-org");
					$sel.empty().append($("<option>").attr("value", DEFAULT_ORG).text(DEFAULT_ORG));
					this._orgs_loaded = true;
					if (done) done();
				},
			});
		}

		_filters() {
			return {
				organization: this.wrapper.find("#afct-org").val() || DEFAULT_ORG,
				fiscal_year: this.wrapper.find("#afct-year").val() || new Date().getFullYear(),
			};
		}

		refresh() {
			const filters = this._filters();
			this.wrapper.find("#afct-refresh").prop("disabled", true);
			frappe.call({
				method: "logistics.air_freight.air_freight_control_tower.get_dashboard_data",
				args: filters,
				callback: (r) => {
					this.wrapper.find("#afct-refresh").prop("disabled", false);
					this.render(r.message || {});
				},
				error: () => {
					this.wrapper.find("#afct-refresh").prop("disabled", false);
					frappe.show_alert({
						message: __("Could not load Air Freight Control Tower data"),
						indicator: "red",
					});
				},
			});
		}

		render(data) {
			const kpis = data.kpis || {};
			this._render_kpis(kpis);
			this._render_airlines(data.top_airlines || [], data.top_airlines_max || 1);
			this._render_returned(kpis, data.fiscal_year);
			this._render_modules(data.by_module || []);
			this._render_links(data.links || {}, data.organization);
			const asOf = data.as_of || "";
			this.wrapper.find("#afct-asof").text(
				asOf
					? __("As of {0} · {1} · FY {2}", [
							frappe.datetime.str_to_user(asOf),
							data.organization || "",
							data.fiscal_year || "",
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
			const html = cards
				.map(
					(c) => `
				<div class="afct-kpi ${c.cls}">
					<p class="afct-kpi-label">${c.label}</p>
					<p class="afct-kpi-value" data-target="${c.value}">${c.format(c.value)}</p>
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
							<div class="afct-airline-fill" style="width:${pct}%; animation-delay:${idx * 0.08}s"></div>
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
				<div class="afct-returned-meta">
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

		_render_links(links, organization) {
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
					route: `/app/query-report/${encodeURIComponent(links.jobs_report)}?organization=${encodeURIComponent(
						organization || DEFAULT_ORG
					)}`,
				});
			}
			if (links.returned_billings_report) {
				items.push({
					label: __("Returned Billings"),
					route: `/app/query-report/${encodeURIComponent(links.returned_billings_report)}?organization=${encodeURIComponent(
						organization || DEFAULT_ORG
					)}`,
				});
			}
			const html = items
				.map((i) => `<a href="${i.route}">${i.label}</a>`)
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
