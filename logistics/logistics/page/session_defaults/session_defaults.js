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
		this.data = {};
		this.fields = {};
		this.field_specs = [];
		this.make();
		this.refresh();
	}

	make() {
		this.$body = $(`
			<div class="logistics-session-defaults">
				<div class="logistics-session-defaults-card">
					<p class="logistics-session-defaults-lead text-muted"></p>
					<div class="logistics-session-defaults-fields"></div>
					<p class="logistics-session-defaults-empty text-muted hide"></p>
					<button type="button" class="btn btn-primary logistics-session-defaults-continue">
						${__("Continue")}
					</button>
				</div>
			</div>
		`).appendTo(this.page.main);
		this.$fields = this.$body.find(".logistics-session-defaults-fields");
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
		const specs = this.data.fields || [];
		this.ensure_fields(specs);
		this.$body.find(".logistics-session-defaults-lead").text(this.lead_text(specs, !!data.required));

		const company_spec = specs.find((spec) => spec.fieldname === "company");
		const companies = company_spec ? this.names_for(company_spec) : [];
		const blocked = !!(company_spec && !companies.length);
		const unconfigured = !specs.length;
		this.$fields.toggleClass("hide", blocked || unconfigured);
		this.$continue.toggleClass("hide", blocked);
		const $empty = this.$body.find(".logistics-session-defaults-empty");
		$empty.toggleClass("hide", !blocked && !unconfigured);
		if (unconfigured) {
			$empty.text(__("Nothing is listed in Session Default Settings."));
			return;
		}
		if (blocked) {
			$empty.text(
				__(
					"No company is available. Ask an administrator to create one before you continue."
				)
			);
			return;
		}

		this._rendering = true;
		if (company_spec) {
			const company = companies.length === 1 ? companies[0] : data.company;
			if (company) {
				this.fields.company.set_value(company);
			}
		}
		this.apply_dimensions(data);
		this._rendering = false;
	}

	lead_text(specs, blocking) {
		const company = specs.find((spec) => spec.fieldname === "company");
		const others = specs
			.filter((spec) => spec.fieldname !== "company")
			.map((spec) => spec.label);
		if (company && !others.length) {
			return blocking
				? __(
						"Choose the company you will work in. Workdesks open after you continue."
					)
				: __("Choose the company you will work in.");
		}
		if (company && others.length) {
			return blocking
				? __(
						"Choose the company you will work in. You can also set {0}. Workdesks open after you continue.",
						[others.join(", ")]
					)
				: __("Choose the company you will work in. You can also set {0}.", [
						others.join(", "),
					]);
		}
		if (!specs.length) {
			return __("Session defaults follow Session Default Settings.");
		}
		return __("Set {0} for this session.", [specs.map((spec) => spec.label).join(", ")]);
	}

	ensure_fields(specs) {
		const signature = specs.map((spec) => spec.fieldname).join("|");
		if (this._signature === signature) {
			return;
		}
		this._signature = signature;
		this.field_specs = specs;
		this.fields = {};
		this.$fields.empty();
		const page = this;
		specs.forEach((spec) => {
			const mark = spec.required ? ' <span class="reqd">*</span>' : "";
			const $field = $(`
				<div class="logistics-session-defaults-field" data-field="${spec.fieldname}">
					<label class="control-label">${spec.label}${mark}</label>
					<div class="logistics-session-defaults-input"></div>
					<p class="logistics-session-defaults-note text-muted small hide"></p>
				</div>
			`).appendTo(this.$fields);
			const control = frappe.ui.form.make_control({
				parent: $field.find(".logistics-session-defaults-input"),
				only_input: true,
				df: {
					fieldtype: "Link",
					fieldname: spec.fieldname,
					options: spec.doctype,
					label: spec.label,
					reqd: spec.required ? 1 : 0,
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
	}

	names_for(spec) {
		const options = (this.data.options || {})[spec.fieldname];
		if (spec.fieldname === "company") {
			return options || this.data.companies || [];
		}
		if (!this.fields.company) {
			return (options || [])
				.filter((row) => row && row.name)
				.map((row) => row.name);
		}
		const company = this.fields.company.get_value();
		return (options || [])
			.filter((row) => row && row.name && (!row.company || row.company === company))
			.map((row) => row.name);
	}

	apply_dimensions(preferred) {
		this.field_specs.forEach((spec) => {
			if (spec.fieldname === "company") {
				return;
			}
			const names = this.names_for(spec);
			const $field = this.$fields.find(`[data-field="${spec.fieldname}"]`);
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
			if (spec.required) {
				$field.find(".reqd").toggleClass("hide", !names.length);
			}
			const company_field = this.fields.company;
			const company = company_field && company_field.get_value();
			$field
				.find(".logistics-session-defaults-note")
				.toggleClass("hide", !company || names.length > 0)
				.text(
					__("No {0} is available for this company. You can continue without one.", [
						spec.label,
					])
				);
		});
	}

	save() {
		if (!this.field_specs.length) {
			logistics.session_defaults.after_save({});
			return;
		}
		const values = {};
		for (const spec of this.field_specs) {
			const value = this.fields[spec.fieldname].get_value();
			if (spec.fieldname === "company" && !value) {
				frappe.msgprint(__("{0} is required", [spec.label]));
				return;
			}
			const missing_required =
				spec.required && spec.fieldname !== "company" && this.names_for(spec).length && !value;
			if (missing_required) {
				frappe.msgprint(__("{0} is required", [spec.label]));
				return;
			}
			values[spec.fieldname] = value || "";
		}
		frappe.call({
			method: "logistics.logistics.page.session_defaults.session_defaults.save_session_defaults",
			args: { values },
			freeze: true,
			freeze_message: __("Saving"),
			callback: (response) => {
				if (!response.message) {
					return;
				}
				logistics.session_defaults.after_save(response.message);
			},
		});
	}
};

logistics.session_defaults.after_save = function (saved) {
	saved = saved || {};
	const applied = saved.applied || {};
	if (frappe.boot) {
		frappe.boot.logistics_needs_session_defaults = 0;
		frappe.boot.user = frappe.boot.user || {};
		frappe.boot.user.defaults = frappe.boot.user.defaults || {};
		Object.keys(applied).forEach((key) => {
			if (!applied[key]) {
				return;
			}
			frappe.boot.user.defaults[key] = applied[key];
		});
		(saved.cleared || []).forEach((key) => {
			delete frappe.boot.user.defaults[key];
		});
	}
	if (frappe.defaults && frappe.defaults.set_user_default_local) {
		Object.keys(applied).forEach((key) => {
			if (!applied[key]) {
				return;
			}
			frappe.defaults.set_user_default_local(key, applied[key]);
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
