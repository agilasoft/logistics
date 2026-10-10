// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt

frappe.provide("logistics.session_defaults");

logistics.session_defaults.FIELDS = [
	{
		fieldname: "company",
		doctype: "Company",
		label: __("Company"),
		list_key: "companies",
	},
	{
		fieldname: "branch",
		doctype: "Branch",
		label: __("Branch"),
		list_key: "branches",
	},
	{
		fieldname: "cost_center",
		doctype: "Cost Center",
		label: __("Cost Center"),
		list_key: "cost_centers",
	},
	{
		fieldname: "profit_center",
		doctype: "Profit Center",
		label: __("Profit Center"),
		list_key: "profit_centers",
	},
];
var SESSION_DEFAULT_FIELDS = logistics.session_defaults.FIELDS;

frappe.pages["session-defaults"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Set up your session"),
		single_column: true,
	});
	wrapper.session_defaults_page = new logistics.session_defaults.SessionDefaultsPage(page);
};

frappe.pages["session-defaults"].on_page_show = function (wrapper) {
	if (wrapper.session_defaults_page) {
		wrapper.session_defaults_page.refresh();
	}
};

logistics.session_defaults.SessionDefaultsPage = class SessionDefaultsPage {
	constructor(page) {
		this.page = page;
		this.data = {};
		this.fields = {};
		this.make();
		this.refresh();
	}

	make() {
		const fields_html = SESSION_DEFAULT_FIELDS.map(
			(spec) => `
				<div class="logistics-session-defaults-field" data-field="${spec.fieldname}">
					<label class="control-label">${spec.label} <span class="reqd">*</span></label>
					<div class="logistics-session-defaults-input"></div>
					<p class="logistics-session-defaults-note text-muted small hide"></p>
				</div>
			`
		).join("");
		this.$body = $(`
			<div class="logistics-session-defaults">
				<div class="logistics-session-defaults-card">
					<p class="logistics-session-defaults-lead text-muted"></p>
					${fields_html}
					<p class="logistics-session-defaults-empty text-muted hide"></p>
					<button type="button" class="btn btn-primary logistics-session-defaults-continue">
						${__("Continue")}
					</button>
				</div>
			</div>
		`).appendTo(this.page.main);

		const page = this;
		SESSION_DEFAULT_FIELDS.forEach((spec) => {
			const $field = this.$body.find(`[data-field="${spec.fieldname}"]`);
			const control = frappe.ui.form.make_control({
				parent: $field.find(".logistics-session-defaults-input"),
				only_input: true,
				df: {
					fieldtype: "Link",
					fieldname: spec.fieldname,
					options: spec.doctype,
					label: spec.label,
					reqd: 1,
					get_query() {
						const names = page.names_for(spec);
						return {
							filters: {
								name: ["in", names.length ? names : ["__no_match__"]],
							},
						};
					},
					onchange() {
						if (spec.fieldname === "company" && !page._rendering) {
							page.apply_dimensions();
						}
					},
				},
				render_input: true,
			});
			this.fields[spec.fieldname] = control;
		});

		this.$continue = this.$body.find(".logistics-session-defaults-continue");
		this.$continue.on("click", (event) => {
			event.preventDefault();
			event.stopPropagation();
			this.save();
		});
	}

	refresh() {
		frappe.call({
			method: "logistics.logistics.page.session_defaults.session_defaults.get_context",
			callback: (response) => this.render(response.message || {}),
		});
	}

	render(data) {
		this.data = data || {};
		const lead = data.required
			? __(
					"Choose the company, branch, cost center, and profit center you will work in. Workdesks open after you continue."
				)
			: __(
					"Choose the company, branch, cost center, and profit center you will work in. New documents use these values."
				);
		this.$body.find(".logistics-session-defaults-lead").text(lead);

		const companies = this.names_for(SESSION_DEFAULT_FIELDS[0]);
		const empty = !companies.length;
		this.$body.find(".logistics-session-defaults-field").toggleClass("hide", empty);
		this.$continue.toggleClass("hide", empty);
		this.$body
			.find(".logistics-session-defaults-empty")
			.toggleClass("hide", !empty)
			.text(
				__(
					"No company is available. Ask an administrator to create one before you continue."
				)
			);
		if (empty) {
			return;
		}

		this._rendering = true;
		const company = companies.length === 1 ? companies[0] : data.company;
		if (company) {
			this.fields.company.set_value(company);
		}
		this.apply_dimensions(data);
		this._rendering = false;
	}

	names_for(spec) {
		if (spec.fieldname === "company") {
			return this.data.companies || [];
		}
		const company = this.fields.company && this.fields.company.get_value();
		return (this.data[spec.list_key] || [])
			.filter((row) => row && row.name && (!row.company || row.company === company))
			.map((row) => row.name);
	}

	apply_dimensions(preferred) {
		SESSION_DEFAULT_FIELDS.forEach((spec) => {
			if (spec.fieldname === "company") {
				return;
			}
			const names = this.names_for(spec);
			const $field = this.$body.find(`[data-field="${spec.fieldname}"]`);
			const control = this.fields[spec.fieldname];
			const current = control.get_value();
			let next = "";
			if (preferred && names.includes(preferred[spec.fieldname])) {
				next = preferred[spec.fieldname];
			} else if (names.includes(current)) {
				next = current;
			} else if (names.length === 1) {
				next = names[0];
			}
			control.set_value(next || "");
			const required = names.length > 0;
			$field.find(".reqd").toggleClass("hide", !required);
			$field
				.find(".logistics-session-defaults-note")
				.toggleClass("hide", required)
				.text(
					__("No {0} is available for this company. You can continue without one.", [
						spec.label,
					])
				);
		});
	}

	save() {
		const company = this.fields.company.get_value();
		if (!company) {
			frappe.msgprint(__("Company is required"));
			return;
		}
		const args = { company };
		for (const spec of SESSION_DEFAULT_FIELDS) {
			if (spec.fieldname === "company") {
				continue;
			}
			const names = this.names_for(spec);
			const value = this.fields[spec.fieldname].get_value();
			if (names.length && !value) {
				frappe.msgprint(__("{0} is required", [spec.label]));
				return;
			}
			args[spec.fieldname] = value || "";
		}
		frappe.call({
			method: "logistics.logistics.page.session_defaults.session_defaults.save_session_defaults",
			args,
			freeze: true,
			freeze_message: __("Saving"),
			callback: (response) => {
				const saved = response.message;
				if (!saved || !saved.company) {
					return;
				}
				logistics.session_defaults.after_save(saved);
			},
		});
	}
};

logistics.session_defaults.after_save = function (saved) {
	const pairs = [
		["Company", "company", saved.company],
		["Branch", "branch", saved.branch],
		["Cost Center", "cost_center", saved.cost_center],
		["Profit Center", "profit_center", saved.profit_center],
	];
	if (frappe.boot) {
		frappe.boot.logistics_needs_session_defaults = 0;
		frappe.boot.user = frappe.boot.user || {};
		frappe.boot.user.defaults = frappe.boot.user.defaults || {};
		pairs.forEach((pair) => {
			if (!pair[2]) {
				return;
			}
			frappe.boot.user.defaults[pair[0]] = pair[2];
			frappe.boot.user.defaults[pair[1]] = pair[2];
		});
	}
	if (frappe.defaults && frappe.defaults.set_user_default_local) {
		pairs.forEach((pair) => {
			if (!pair[2]) {
				return;
			}
			frappe.defaults.set_user_default_local(pair[0], pair[2]);
			frappe.defaults.set_user_default_local(pair[1], pair[2]);
		});
	}
	document.body.classList.remove("logistics-needs-session-defaults");

	const route =
		logistics.session_defaults.consume_return_route &&
		logistics.session_defaults.consume_return_route();
	if (route && route.length) {
		frappe.set_route(route);
		return;
	}
	frappe.set_route(logistics.session_defaults.HOME || "/desk/transport");
};
