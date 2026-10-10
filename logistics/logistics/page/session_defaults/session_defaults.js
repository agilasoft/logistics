// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt

frappe.provide("logistics.session_defaults");

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
		this.companies = [];
		this.make();
		this.refresh();
	}

	make() {
		this.$body = $(`
			<div class="logistics-session-defaults">
				<div class="logistics-session-defaults-card">
					<p class="logistics-session-defaults-lead text-muted"></p>
					<div class="logistics-session-defaults-field"></div>
					<p class="logistics-session-defaults-empty text-muted hide"></p>
					<button type="button" class="btn btn-primary logistics-session-defaults-continue">
						${__("Continue")}
					</button>
				</div>
			</div>
		`).appendTo(this.page.main);

		const page = this;
		this.company_field = frappe.ui.form.make_control({
			parent: this.$body.find(".logistics-session-defaults-field"),
			df: {
				fieldtype: "Link",
				fieldname: "company",
				options: "Company",
				label: __("Company"),
				reqd: 1,
				get_query() {
					if (!page.companies.length) {
						return {};
					}
					return { filters: { name: ["in", page.companies] } };
				},
			},
			render_input: true,
		});

		this.$continue = this.$body.find(".logistics-session-defaults-continue");
		this.$continue.on("click", () => this.save());
	}

	refresh() {
		frappe.call({
			method: "logistics.logistics.page.session_defaults.session_defaults.get_context",
			callback: (response) => this.render(response.message || {}),
		});
	}

	render(data) {
		this.companies = data.companies || [];
		const lead = data.required
			? __("Choose the company you will work in. Workdesks open after you continue.")
			: __("Choose the company you will work in. New documents and reports use this company.");
		this.$body.find(".logistics-session-defaults-lead").text(lead);

		const empty = !this.companies.length;
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
		const current = this.companies.length === 1 ? this.companies[0] : data.company;
		if (current) {
			this.company_field.set_value(current);
		}
	}

	save() {
		const company = this.company_field.get_value();
		if (!company) {
			frappe.msgprint(__("Company is required"));
			return;
		}
		frappe.call({
			method: "logistics.logistics.page.session_defaults.session_defaults.save_session_defaults",
			args: { company },
			freeze: true,
			freeze_message: __("Saving"),
			callback: (response) => {
				const saved = response.message && response.message.company;
				if (!saved) {
					return;
				}
				logistics.session_defaults.after_save(saved);
			},
		});
	}
};

logistics.session_defaults.after_save = function (company) {
	if (frappe.boot) {
		frappe.boot.logistics_needs_session_defaults = 0;
		frappe.boot.user = frappe.boot.user || {};
		frappe.boot.user.defaults = frappe.boot.user.defaults || {};
		frappe.boot.user.defaults.Company = company;
		frappe.boot.user.defaults.company = company;
	}
	if (frappe.defaults && frappe.defaults.set_user_default_local) {
		frappe.defaults.set_user_default_local("Company", company);
		frappe.defaults.set_user_default_local("company", company);
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
