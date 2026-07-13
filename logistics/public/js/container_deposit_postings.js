// Copyright (c) 2026, Logistics Team and contributors
// Filterable Transaction Postings grid for Container → Container Deposit tab.

(function () {
	const PAGE_LENGTH_OPTIONS = [10, 25, 50, 100];

	function inject_styles() {
		if (document.getElementById("cd-postings-styles")) {
			return;
		}
		const css =
			".cd-postings{margin-top:4px;}" +
			".cd-postings-header{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px;}" +
			".cd-postings-header h6{margin:0;font-size:13px;font-weight:600;}" +
			".cd-postings-header .cd-subtitle{font-size:12px;color:var(--text-muted,#64748b);margin-top:2px;}" +
			".cd-postings-actions{display:flex;gap:8px;flex-shrink:0;}" +
			".cd-filter-bar{display:flex;align-items:flex-end;flex-wrap:wrap;gap:12px;padding:12px;background:var(--fg-color,#fff);border:1px solid var(--border-color,#e2e8f0);border-radius:8px;margin-bottom:12px;}" +
			".cd-filter-field{display:flex;flex-direction:column;gap:4px;min-width:140px;}" +
			".cd-filter-field label{font-size:11px;font-weight:600;color:var(--text-muted,#64748b);margin:0;}" +
			".cd-filter-field select,.cd-filter-field input{font-size:12px;padding:5px 8px;border-radius:6px;border:1px solid var(--border-color,#e2e8f0);background:var(--control-bg,#fff);min-height:30px;}" +
			".cd-filter-field.cd-date-range{min-width:260px;}" +
			".cd-date-inputs{display:flex;align-items:center;gap:6px;}" +
			".cd-summary-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:12px;}" +
			".cd-summary-card{display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:10px;border:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#fff);box-shadow:0 1px 2px rgba(15,23,42,0.04);}" +
			".cd-summary-icon{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;}" +
			".cd-summary-card.deposited .cd-summary-icon{background:#eff6ff;color:#2563eb;}" +
			".cd-summary-card.refunded .cd-summary-icon{background:#ecfdf5;color:#059669;}" +
			".cd-summary-card.pending .cd-summary-icon{background:#fff7ed;color:#ea580c;}" +
			".cd-summary-label{font-size:11px;color:var(--text-muted,#64748b);}" +
			".cd-summary-value{font-size:18px;font-weight:700;line-height:1.2;}" +
			".cd-summary-caption{font-size:11px;color:var(--text-muted,#64748b);margin-bottom:10px;}" +
			".cd-table-wrap{border:1px solid var(--border-color,#e2e8f0);border-radius:8px;overflow:hidden;background:var(--fg-color,#fff);}" +
			".cd-table{width:100%;margin:0;font-size:12px;}" +
			".cd-table thead th{background:var(--subtle-fg,#f8fafc);font-weight:600;white-space:nowrap;}" +
			".cd-table td,.cd-table th{padding:8px 10px;vertical-align:middle;}" +
			".cd-table tbody tr:hover{background:var(--subtle-fg,#f8fafc);}" +
			".cd-voucher-link{font-weight:500;}" +
			".cd-badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;}" +
			".cd-badge.open{background:#fef3c7;color:#b45309;}" +
			".cd-badge.refunded{background:#dcfce7;color:#15803d;}" +
			".cd-table-footer{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 12px;border-top:1px solid var(--border-color,#e2e8f0);font-size:12px;color:var(--text-muted,#64748b);}" +
			".cd-pagination{display:flex;align-items:center;gap:4px;}" +
			".cd-pagination button{min-width:28px;height:28px;padding:0 6px;border:1px solid var(--border-color,#e2e8f0);border-radius:6px;background:var(--control-bg,#fff);font-size:12px;}" +
			".cd-pagination button.active{background:var(--primary,#171717);color:#fff;border-color:var(--primary,#171717);}" +
			".cd-pagination button:disabled{opacity:0.45;cursor:not-allowed;}" +
			".cd-info-note{margin-top:12px;padding:10px 12px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;font-size:12px;color:#1e40af;}" +
			".cd-empty{padding:24px;text-align:center;color:var(--text-muted,#64748b);font-size:12px;}" +
			"@media (max-width:900px){.cd-summary-row{grid-template-columns:1fr;}}";
		$("head").append(`<style id="cd-postings-styles">${css}</style>`);
	}

	function voucher_route(voucher_type, voucher_no) {
		const map = {
			"Purchase Invoice": "purchase-invoice",
			"Journal Entry": "journal-entry",
		};
		const slug = map[voucher_type];
		if (!slug || !voucher_no) {
			return null;
		}
		return `/app/${slug}/${encodeURIComponent(voucher_no)}`;
	}

		function default_filters(items) {
		return {
			items: items.slice(),
			voucher_types: ["Purchase Invoice", "Journal Entry"],
			from_date: "",
			to_date: "",
			refund_statuses: ["Open", "Refunded"],
			page: 1,
			page_length: 10,
		};
	}

	function row_matches_filters(row, filters) {
		if (filters.items.length && row.item_code && filters.items.indexOf(row.item_code) === -1) {
			return false;
		}
		if (
			filters.voucher_types.length &&
			filters.voucher_types.indexOf(row.voucher_type) === -1
		) {
			return false;
		}
		if (filters.from_date && row.posting_date && row.posting_date < filters.from_date) {
			return false;
		}
		if (filters.to_date && row.posting_date && row.posting_date > filters.to_date) {
			return false;
		}
		if (filters.refund_statuses.length) {
			const status = row.refund_status || "";
			if (status && filters.refund_statuses.indexOf(status) === -1) {
				return false;
			}
			if (!status && filters.refund_statuses.length < 2) {
				return false;
			}
		}
		return true;
	}

	class ContainerDepositPostings {
		constructor(frm) {
			this.frm = frm;
			this.$wrapper = frm.fields_dict.deposits_gl_html.$wrapper;
			this.data = { rows: [], items: [], currency: null, error: null };
			this.filters = default_filters([]);
			this.sort = { field: "posting_date", asc: false };
		}

		refresh() {
			inject_styles();
			this.$wrapper.empty().append(`<div class="cd-postings"><div class="text-muted small">${__(
				"Loading transaction postings…"
			)}</div></div>`);
			frappe.call({
				method: "logistics.logistics.doctype.container.container.get_deposit_postings_data",
				args: { container: this.frm.doc.name },
				callback: (r) => {
					this.data = r.message || { rows: [], items: [], currency: null, error: null };
					this.filters = default_filters(this.data.items || []);
					this.render();
				},
			});
		}

		render() {
			const $root = $('<div class="cd-postings"></div>');
			if (this.data.error) {
				$root.append(`<p class="text-muted">${frappe.utils.escape_html(this.data.error)}</p>`);
				this.$wrapper.empty().append($root);
				return;
			}
			$root.append(this._render_header());
			$root.append(this._render_filters());
			$root.append(this._render_summary());
			$root.append(this._render_table());
			$root.append(this._render_info_note());
			this.$wrapper.empty().append($root);
		}

		_render_header() {
			const $header = $(`
				<div class="cd-postings-header">
					<div>
						<h6>${__("Transaction Postings")}</h6>
						<div class="cd-subtitle">${__(
							"Container deposit transaction postings — deposit charges only."
						)}</div>
					</div>
					<div class="cd-postings-actions">
						<button type="button" class="btn btn-default btn-sm btn-refresh">${__("Refresh")}</button>
					</div>
				</div>
			`);
			$header.find(".btn-refresh").on("click", () => this.refresh());
			return $header;
		}

		_render_filters() {
			const items = this.data.items || [];
			const $bar = $('<div class="cd-filter-bar"></div>');

			const $item = $(`
				<div class="cd-filter-field">
					<label>${__("Item")}</label>
					<select class="cd-filter-items"></select>
				</div>
			`);
			$item.find("select").append(`<option value="__all__">${__("All Container Deposit Items")}</option>`);
			items.forEach((code) => {
				$item.find("select").append(
					`<option value="${frappe.utils.escape_html(code)}">${frappe.utils.escape_html(code)}</option>`
				);
			});
			$item.find("select").val(
				this.filters.items.length === 1 && items.indexOf(this.filters.items[0]) !== -1
					? this.filters.items[0]
					: "__all__"
			);

			const $voucher = $(`
				<div class="cd-filter-field">
					<label>${__("Voucher Type")}</label>
					<select class="cd-filter-voucher" multiple size="2">
						<option value="Purchase Invoice">${__("Purchase Invoice")}</option>
						<option value="Journal Entry">${__("Journal Entry")}</option>
					</select>
				</div>
			`);
			$voucher.find("select").val(this.filters.voucher_types);

			const $dates = $(`
				<div class="cd-filter-field cd-date-range">
					<label>${__("Date Range")}</label>
					<div class="cd-date-inputs">
						<input type="date" class="cd-filter-from" />
						<span>–</span>
						<input type="date" class="cd-filter-to" />
					</div>
				</div>
			`);
			$dates.find(".cd-filter-from").val(this.filters.from_date || "");
			$dates.find(".cd-filter-to").val(this.filters.to_date || "");

			const $status = $(`
				<div class="cd-filter-field">
					<label>${__("Refund Status")}</label>
					<select class="cd-filter-status" multiple size="2">
						<option value="Open">${__("Open")}</option>
						<option value="Refunded">${__("Refunded")}</option>
					</select>
				</div>
			`);
			$status.find("select").val(this.filters.refund_statuses);

			const $clear = $(`
				<div class="cd-filter-field">
					<label>&nbsp;</label>
					<button type="button" class="btn btn-default btn-sm">${__("Clear Filters")}</button>
				</div>
			`);

			$bar.append($item, $voucher, $dates, $status, $clear);

			const apply = () => {
				const selectedItem = $item.find("select").val() || "__all__";
				this.filters.items =
					selectedItem === "__all__" ? (this.data.items || []).slice() : [selectedItem];
				this.filters.voucher_types = $voucher.find("select").val() || [];
				this.filters.from_date = $dates.find(".cd-filter-from").val() || "";
				this.filters.to_date = $dates.find(".cd-filter-to").val() || "";
				this.filters.refund_statuses = $status.find("select").val() || [];
				this.filters.page = 1;
				this._rerender_body();
			};

			$bar.find("select, input").on("change", apply);
			$clear.find("button").on("click", () => {
				this.filters = default_filters(this.data.items || []);
				this.render();
			});

			return $bar;
		}

		_filtered_rows() {
			let rows = (this.data.rows || []).filter((row) => row_matches_filters(row, this.filters));
			const field = this.sort.field;
			const dir = this.sort.asc ? 1 : -1;
			rows.sort((a, b) => {
				const av = a[field];
				const bv = b[field];
				if (field === "debit" || field === "credit") {
					return (flt(av) - flt(bv)) * dir;
				}
				return String(av || "").localeCompare(String(bv || "")) * dir;
			});
			return rows;
		}

		_format_currency(amount) {
			const currency = this.data.currency || frappe.defaults.get_default("currency");
			return format_currency(flt(amount), currency);
		}

		_render_summary() {
			const rows = this._filtered_rows();
			const total_deposited = rows.reduce((sum, row) => sum + flt(row.debit), 0);
			const total_refunded = rows.reduce((sum, row) => sum + flt(row.credit), 0);
			const net_pending = total_deposited - total_refunded;
			const $wrap = $(`
				<div>
					<div class="cd-summary-row">
						<div class="cd-summary-card deposited">
							<div class="cd-summary-icon">↓</div>
							<div>
								<div class="cd-summary-label">${__("Total Deposited")}</div>
								<div class="cd-summary-value">${this._format_currency(total_deposited)}</div>
							</div>
						</div>
						<div class="cd-summary-card refunded">
							<div class="cd-summary-icon">↻</div>
							<div>
								<div class="cd-summary-label">${__("Total Refunded")}</div>
								<div class="cd-summary-value">${this._format_currency(total_refunded)}</div>
							</div>
						</div>
						<div class="cd-summary-card pending">
							<div class="cd-summary-icon">⊟</div>
							<div>
								<div class="cd-summary-label">${__("Net Pending")}</div>
								<div class="cd-summary-value">${this._format_currency(net_pending)}</div>
							</div>
						</div>
					</div>
					<div class="cd-summary-caption">${__("Summary is based on the selected filters.")}</div>
				</div>
			`);
			$wrap.find(".cd-summary-row").attr("data-cd-part", "summary");
			return $wrap;
		}

		_render_table() {
			const rows = this._filtered_rows();
			const page_length = cint(this.filters.page_length) || 10;
			const total = rows.length;
			const total_pages = Math.max(1, Math.ceil(total / page_length));
			if (this.filters.page > total_pages) {
				this.filters.page = total_pages;
			}
			const start = (this.filters.page - 1) * page_length;
			const page_rows = rows.slice(start, start + page_length);

			const $wrap = $('<div class="cd-table-wrap" data-cd-part="table"></div>');
			if (!total) {
				$wrap.append(`<div class="cd-empty">${__("No transaction postings match the selected filters.")}</div>`);
				return $wrap;
			}

			const $table = $(`
				<table class="table cd-table">
					<thead>
						<tr>
							<th>#</th>
							<th class="cd-sort" data-field="posting_date">${__("Date")}</th>
							<th class="cd-sort" data-field="voucher_type">${__("Voucher Type")}</th>
							<th>${__("Voucher No.")}</th>
							<th class="cd-sort" data-field="item_code">${__("Item")}</th>
							<th>${__("Account")}</th>
							<th class="cd-sort text-right" data-field="debit">${__("Debit")}</th>
							<th class="cd-sort text-right" data-field="credit">${__("Credit")}</th>
							<th>${__("Party")}</th>
							<th>${__("Refund Status")}</th>
						</tr>
					</thead>
					<tbody></tbody>
				</table>
			`);

			const $tbody = $table.find("tbody");
			page_rows.forEach((row, idx) => {
				const route = voucher_route(row.voucher_type, row.voucher_no);
				const voucher_html = route
					? `<a class="cd-voucher-link" href="${route}">${frappe.utils.escape_html(
							row.voucher_no
					  )}</a>`
					: frappe.utils.escape_html(row.voucher_no || "");
				let badge = "";
				if (row.refund_status === "Open") {
					badge = `<span class="cd-badge open">${__("Open")}</span>`;
				} else if (row.refund_status === "Refunded") {
					badge = `<span class="cd-badge refunded">${__("Refunded")}</span>`;
				}
				$tbody.append(`
					<tr>
						<td>${start + idx + 1}</td>
						<td>${row.posting_date ? frappe.datetime.str_to_user(row.posting_date) : ""}</td>
						<td>${frappe.utils.escape_html(row.voucher_type || "")}</td>
						<td>${voucher_html}</td>
						<td>${frappe.utils.escape_html(row.item_code || "")}</td>
						<td>${frappe.utils.escape_html(row.account_label || row.account || "")}</td>
						<td class="text-right">${row.debit ? this._format_currency(row.debit) : ""}</td>
						<td class="text-right">${row.credit ? this._format_currency(row.credit) : ""}</td>
						<td>${frappe.utils.escape_html(row.party || "")}</td>
						<td>${badge}</td>
					</tr>
				`);
			});

			$table.find(".cd-sort").on("click", (e) => {
				const field = $(e.currentTarget).data("field");
				if (this.sort.field === field) {
					this.sort.asc = !this.sort.asc;
				} else {
					this.sort.field = field;
					this.sort.asc = true;
				}
				this._rerender_body();
			});

			$wrap.append($table);
			$wrap.append(this._render_footer(total, start, page_rows.length, total_pages));
			return $wrap;
		}

		_render_footer(total, start, shown, total_pages) {
			const $footer = $(`
				<div class="cd-table-footer">
					<div>${__(
						"Showing {0} to {1} of {2} entries",
						[total ? start + 1 : 0, start + shown, total]
					)}</div>
					<div class="cd-pagination"></div>
					<div>
						<select class="cd-page-length">
							${PAGE_LENGTH_OPTIONS.map(
								(n) =>
									`<option value="${n}" ${
										cint(this.filters.page_length) === n ? "selected" : ""
									}>${n} / ${__("page")}</option>`
							).join("")}
						</select>
					</div>
				</div>
			`);

			const $pagination = $footer.find(".cd-pagination");
			const page = cint(this.filters.page) || 1;
			$pagination.append(
				`<button type="button" data-page="prev" ${page <= 1 ? "disabled" : ""}>&lt;</button>`
			);
			for (let p = 1; p <= total_pages && p <= 7; p += 1) {
				$pagination.append(
					`<button type="button" data-page="${p}" class="${p === page ? "active" : ""}">${p}</button>`
				);
			}
			if (total_pages > 7) {
				$pagination.append(`<span>…</span>`);
				$pagination.append(
					`<button type="button" data-page="${total_pages}" class="${
						total_pages === page ? "active" : ""
					}">${total_pages}</button>`
				);
			}
			$pagination.append(
				`<button type="button" data-page="next" ${
					page >= total_pages ? "disabled" : ""
				}>&gt;</button>`
			);

			$pagination.find("button[data-page]").on("click", (e) => {
				const target = $(e.currentTarget).data("page");
				if (target === "prev") {
					this.filters.page = Math.max(1, page - 1);
				} else if (target === "next") {
					this.filters.page = Math.min(total_pages, page + 1);
				} else {
					this.filters.page = cint(target);
				}
				this._rerender_body();
			});

			$footer.find(".cd-page-length").on("change", (e) => {
				this.filters.page_length = cint(e.target.value) || 10;
				this.filters.page = 1;
				this._rerender_body();
			});

			return $footer;
		}

		_render_info_note() {
			return $(`
				<div class="cd-info-note" data-cd-part="info">
					${__(
						"Only container deposit charges (e.g. CONDEP and other deposit items) are included in this view."
					)}
				</div>
			`);
		}

		_rerender_body() {
			this.$wrapper.find("[data-cd-part=summary]").parent().replaceWith(this._render_summary());
			this.$wrapper.find("[data-cd-part=table]").replaceWith(this._render_table());
		}
	}

	window.logistics = window.logistics || {};
	window.logistics.container_deposit_postings = {
		render(frm) {
			if (!frm.fields_dict.deposits_gl_html) {
				return;
			}
			if (!frm._cd_postings_widget) {
				frm._cd_postings_widget = new ContainerDepositPostings(frm);
			}
			frm._cd_postings_widget.refresh();
		},
	};
})();
