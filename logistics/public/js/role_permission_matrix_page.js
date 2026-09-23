// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
// Role Permission Matrix — editable DocType × rights table

frappe.provide("logistics.role_permission_matrix");

logistics.role_permission_matrix.RolePermissionMatrixPage = class RolePermissionMatrixPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Role Permission Matrix"),
			single_column: true,
		});
		this.$body = $(wrapper).find(".layout-main-section");
		this.rights = (frappe.perm && frappe.perm.rights ? frappe.perm.rights.slice() : []).filter(
			(r) => r !== "mask"
		);
		if (!this.rights.length) {
			this.rights = [
				"select",
				"read",
				"write",
				"create",
				"delete",
				"submit",
				"cancel",
				"amend",
				"report",
				"import",
				"export",
				"print",
				"email",
				"share",
			];
		}
		this.SUBMIT_RIGHTS = ["submit", "cancel", "amend"];
		this.all_rows = [];
		this.filtered_rows = [];
		this.options = { roles: [], doctypes: [], modules: [] };
		this.filters = { role: "", module: "", search: "" };
		this.user_count = 0;
		this._search_timer = null;
		this._loading = false;
		this._pending_toggles = new Set();

		this.render_shell();
		this.setup_filter_controls();
		this.load_options().then(() => {
			this.bind_events();
			if (frappe.route_options && frappe.route_options.role) {
				this.filters.role = frappe.route_options.role;
				this.role_control.set_value(this.filters.role);
				frappe.route_options = null;
			}
			if (this.filters.role) {
				this.load_matrix();
			} else {
				this.render_empty(__("Select a Role to view and edit permissions."));
			}
		});
	}

	api(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: `logistics.logistics.page.role_permission_matrix.role_permission_matrix.${method}`,
				args: args || {},
				callback: (r) => {
					if (r.exc) {
						reject(r);
					} else {
						resolve(r);
					}
				},
				error: (r) => reject(r),
			});
		});
	}

	pm(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				module: "frappe.core",
				page: "permission_manager",
				method: method,
				args: args || {},
				callback: (r) => {
					if (r.exc) {
						reject(r);
					} else {
						resolve(r);
					}
				},
				error: (r) => reject(r),
			});
		});
	}

	render_shell() {
		this.$body.html(`
			<div class="rpm-page">
				<div class="rpm-toolbar">
					<div class="rpm-filters">
						<div class="rpm-field" data-field="role"></div>
						<div class="rpm-field" data-field="module"></div>
						<div class="rpm-field rpm-field-search" data-field="search"></div>
					</div>
					<div class="rpm-actions">
						<button type="button" class="btn btn-default btn-xs rpm-refresh">
							${frappe.utils.icon("refresh", "xs")} ${__("Refresh")}
						</button>
						<button type="button" class="btn btn-primary btn-xs rpm-add">
							${frappe.utils.icon("add", "xs")} ${__("Add DocType")}
						</button>
					</div>
				</div>
				<div class="rpm-loading text-muted" style="display:none;">
					${__("Loading permissions…")}
				</div>
				<div class="rpm-table-wrap">
					<div class="rpm-table-scroll">
						<table class="rpm-table">
							<thead></thead>
							<tbody></tbody>
						</table>
					</div>
					<div class="rpm-empty text-muted" style="display:none;"></div>
				</div>
				<div class="rpm-footer">
					<div class="rpm-footer-left">
						<span class="rpm-summary"></span>
					</div>
				</div>
				<div class="rpm-banner">
					<span class="rpm-banner-icon">${frappe.utils.icon("info", "sm")}</span>
					<span class="rpm-banner-text">
						${__(
							"Changes are saved automatically. Permissions are applied immediately to all users with this role."
						)}
					</span>
					<a class="rpm-banner-link" href="/app/permission-manager">
						${__("Open Role Permissions Manager")}
					</a>
				</div>
			</div>
		`);

		this.$loading = this.$body.find(".rpm-loading");
		this.$thead = this.$body.find(".rpm-table thead");
		this.$tbody = this.$body.find(".rpm-table tbody");
		this.$empty = this.$body.find(".rpm-empty");
		this.$summary = this.$body.find(".rpm-summary");
		this.render_header();
	}

	setup_filter_controls() {
		this.role_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="role"]'),
			df: {
				fieldtype: "Link",
				options: "Role",
				fieldname: "role",
				label: __("Role"),
				placeholder: __("Select Role"),
				input_class: "input-xs",
				change: () => {
					const value = this.role_control.get_value() || "";
					if (value === this.filters.role) {
						return;
					}
					this.filters.role = value;
					this.load_matrix();
				},
			},
			render_input: true,
		});
		this.role_control.$input.addClass("input-xs");

		this.module_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="module"]'),
			df: {
				fieldtype: "Link",
				options: "Module Def",
				fieldname: "module",
				label: __("Module"),
				placeholder: __("All Modules"),
				input_class: "input-xs",
				change: () => {
					const value = this.module_control.get_value() || "";
					if (value === this.filters.module) {
						return;
					}
					this.filters.module = value;
					this.load_matrix();
				},
			},
			render_input: true,
		});
		this.module_control.$input.addClass("input-xs");

		this.search_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="search"]'),
			df: {
				fieldtype: "Data",
				fieldname: "search_doctype",
				label: __("Search DocType"),
				placeholder: __("Search DocType…"),
				input_class: "input-xs",
			},
			render_input: true,
		});
		this.search_control.$input.addClass("input-xs rpm-search");
		this.$search = this.search_control.$input;
	}

	render_header() {
		const right_ths = this.rights
			.map((r) => `<th class="rpm-col-right">${__(frappe.unscrub(r))}</th>`)
			.join("");
		this.$thead.html(`
			<tr>
				<th class="rpm-col-idx">#</th>
				<th class="rpm-col-doctype">${__("Document Type")}</th>
				<th class="rpm-col-level">${__("Level")}</th>
				<th class="rpm-col-right">${__("If Owner")}</th>
				${right_ths}
				<th class="rpm-col-actions"></th>
			</tr>
		`);
	}

	load_options() {
		return this.api("get_filter_options").then((r) => {
			this.options = r.message || { roles: [], doctypes: [], modules: [] };
		});
	}

	bind_events() {
		this.$search.on("input", () => {
			clearTimeout(this._search_timer);
			this._search_timer = setTimeout(() => {
				this.filters.search = (this.$search.val() || "").trim().toLowerCase();
				this.apply_filters_and_render();
			}, 200);
		});
		this.$body.find(".rpm-refresh").on("click", () => this.load_matrix());
		this.$body.find(".rpm-add").on("click", () => this.prompt_add_doctype());
		// Use click on checkbox — more reliable than change with custom UI
		this.$tbody.on("click", "input.rpm-check", (e) => {
			e.stopPropagation();
			const $input = $(e.currentTarget);
			// Let browser toggle first, then persist
			setTimeout(() => this.on_toggle($input), 0);
		});
		this.$tbody.on("click", ".rpm-row-menu-btn", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this.toggle_row_menu($(e.currentTarget));
		});
		this.$tbody.on("click", ".rpm-remove-row", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const $btn = $(e.currentTarget);
			this.remove_row({
				parent: $btn.attr("data-doctype"),
				role: $btn.attr("data-role"),
				permlevel: cint($btn.attr("data-permlevel")),
				if_owner: cint($btn.attr("data-if_owner")),
			});
		});
		$(document)
			.off("click.rpm_menu")
			.on("click.rpm_menu", () => this.$tbody.find(".rpm-row-menu").removeClass("open"));
	}

	refresh() {
		// Avoid re-entrant freeze when navigating back to the page
		if (this.filters.role && !this._loading) {
			this.load_matrix();
		}
	}

	set_loading(loading) {
		this._loading = !!loading;
		this.$loading.toggle(!!loading);
		this.$body.find(".rpm-table-wrap").toggleClass("rpm-dim", !!loading);
	}

	load_matrix() {
		if (!this.filters.role) {
			this.all_rows = [];
			this.filtered_rows = [];
			this.user_count = 0;
			this.render_empty(__("Select a Role to view and edit permissions."));
			return Promise.resolve();
		}
		this.set_loading(true);
		return this.api("get_matrix", {
			role: this.filters.role,
			module: this.filters.module || null,
		})
			.then((r) => {
				this.all_rows = (r.message || []).filter((d) => d.parent !== "DocType");
				return this.pm("get_users_with_role", { role: this.filters.role }).catch(() => ({
					message: [],
				}));
			})
			.then((r) => {
				this.user_count = ((r && r.message) || []).length;
				this.apply_filters_and_render();
			})
			.catch(() => {
				frappe.show_alert({
					message: __("Could not load permissions."),
					indicator: "red",
				});
			})
			.finally(() => this.set_loading(false));
	}

	apply_filters_and_render() {
		const search = this.filters.search;
		// Module filtering is done server-side when module is set
		this.filtered_rows = this.all_rows.filter((row) => {
			if (search) {
				const name = (row.parent || "").toLowerCase();
				if (!name.includes(search)) {
					return false;
				}
			}
			return true;
		});
		this.render_table();
	}

	render_empty(message) {
		this.$tbody.empty();
		this.$empty.text(message).show();
		this.update_summary(0);
	}

	update_summary(total) {
		if (!this.filters.role) {
			this.$summary.text("");
			return;
		}
		const docs =
			total === 1 ? __("Showing 1 DocType") : __("Showing {0} DocTypes", [total]);
		const users =
			this.user_count === 1
				? __("1 user has this role")
				: __("{0} users have this role", [this.user_count]);
		this.$summary.text(`${docs} · ${users}`);
	}

	render_table() {
		const total = this.filtered_rows.length;

		if (!this.filters.role) {
			this.render_empty(__("Select a Role to view and edit permissions."));
			return;
		}
		if (!total) {
			this.render_empty(
				this.filters.module
					? __("No DocTypes found for this module.")
					: __("No permissions set for this criteria. Use Add DocType, or filter by Module to see every DocType in that module.")
			);
			return;
		}

		this.$empty.hide();
		this.$tbody.html(this.filtered_rows.map((row, i) => this.row_html(row, i + 1)).join(""));
		this.update_summary(total);
	}

	row_html(row, idx) {
		const doctype = row.parent;
		const role = row.role || this.filters.role;
		const level = cint(row.permlevel);
		const if_owner = cint(row.if_owner);
		const is_submittable = cint(row.is_submittable);
		const is_placeholder = cint(row._is_placeholder);

		const if_owner_cell = this.checkbox_html({
			ptype: "if_owner",
			checked: if_owner,
			doctype,
			role,
			permlevel: level,
			if_owner,
			applicable: level === 0,
			is_placeholder,
		});

		const right_cells = this.rights
			.map((ptype) => {
				let show = true;
				if (level > 0 && !["read", "write"].includes(ptype)) {
					show = false;
				}
				if (this.SUBMIT_RIGHTS.includes(ptype) && !is_submittable) {
					show = false;
				}
				return `<td class="rpm-col-right">${this.checkbox_html({
					ptype,
					checked: cint(row[ptype]),
					doctype,
					role,
					permlevel: level,
					if_owner,
					applicable: show,
					is_placeholder,
				})}</td>`;
			})
			.join("");

		return `
			<tr data-doctype="${frappe.utils.escape_html(doctype)}"
				data-role="${frappe.utils.escape_html(role)}"
				data-permlevel="${level}"
				data-if_owner="${if_owner}"
				data-placeholder="${is_placeholder}">
				<td class="rpm-col-idx">${idx}</td>
				<td class="rpm-col-doctype">
					<a href="/app/${frappe.router.slug(doctype)}">
						${frappe.utils.escape_html(__(doctype))}
					</a>
					${
						is_placeholder
							? `<span class="rpm-placeholder">${__("no permission yet")}</span>`
							: ""
					}
				</td>
				<td class="rpm-col-level">${level}</td>
				<td class="rpm-col-right">${if_owner_cell}</td>
				${right_cells}
				<td class="rpm-col-actions">
					${
						is_placeholder
							? ""
							: `<div class="rpm-row-menu">
						<button type="button" class="btn btn-xs rpm-row-menu-btn" title="${__("Actions")}">
							${frappe.utils.icon("dot-horizontal", "sm")}
						</button>
						<div class="rpm-row-menu-dropdown">
							<button type="button" class="rpm-remove-row"
								data-doctype="${frappe.utils.escape_html(doctype)}"
								data-role="${frappe.utils.escape_html(role)}"
								data-permlevel="${level}"
								data-if_owner="${if_owner}">
								${__("Remove")}
							</button>
						</div>
					</div>`
					}
				</td>
			</tr>
		`;
	}

	checkbox_html({ ptype, checked, doctype, role, permlevel, if_owner, applicable, is_placeholder }) {
		if (!applicable) {
			return `<span class="rpm-na">-</span>`;
		}
		return `
			<label class="rpm-check-label">
				<input
					type="checkbox"
					class="rpm-check"
					data-ptype="${frappe.utils.escape_html(ptype)}"
					data-doctype="${frappe.utils.escape_html(doctype)}"
					data-role="${frappe.utils.escape_html(role)}"
					data-permlevel="${permlevel}"
					data-if_owner="${if_owner}"
					data-placeholder="${is_placeholder ? 1 : 0}"
					${checked ? "checked" : ""}
				/>
				<span class="rpm-check-ui" aria-hidden="true"></span>
			</label>
		`;
	}

	toggle_row_menu($btn) {
		const $menu = $btn.closest(".rpm-row-menu");
		const was_open = $menu.hasClass("open");
		this.$tbody.find(".rpm-row-menu").removeClass("open");
		if (!was_open) {
			$menu.addClass("open");
		}
	}

	toggle_key($input) {
		return [
			$input.attr("data-doctype"),
			$input.attr("data-ptype"),
			$input.attr("data-permlevel"),
			$input.attr("data-if_owner"),
		].join("::");
	}

	async on_toggle($input) {
		const key = this.toggle_key($input);
		if (this._pending_toggles.has(key)) {
			return;
		}
		this._pending_toggles.add(key);
		$input.prop("disabled", true);

		const args = {
			role: $input.attr("data-role"),
			permlevel: cint($input.attr("data-permlevel")),
			doctype: $input.attr("data-doctype"),
			ptype: $input.attr("data-ptype"),
			value: $input.prop("checked") ? 1 : 0,
			if_owner: cint($input.attr("data-if_owner")),
		};
		const is_placeholder = cint($input.attr("data-placeholder"));

		try {
			if (is_placeholder && args.value) {
				await this.pm("add", {
					parent: args.doctype,
					role: args.role,
					permlevel: args.permlevel,
				});
				// Newly added rows start with default rights — apply the toggled right
				await this.pm("update", args);
				await this.load_matrix();
				frappe.show_alert({ message: __("Permission saved"), indicator: "green" });
				return;
			}

			if (is_placeholder && !args.value) {
				return;
			}

			const r = await this.pm("update", args);
			const row = this.all_rows.find(
				(d) =>
					d.parent === args.doctype &&
					cint(d.permlevel) === args.permlevel &&
					cint(d.if_owner) === args.if_owner
			);
			if (row) {
				row[args.ptype] = args.value;
				row._is_placeholder = 0;
			}
			if (args.ptype === "if_owner" || r.message === "refresh") {
				await this.load_matrix();
			}
		} catch (e) {
			$input.prop("checked", !args.value);
			frappe.show_alert({
				message: __("Could not update permission."),
				indicator: "red",
			});
		} finally {
			$input.prop("disabled", false);
			this._pending_toggles.delete(key);
		}
	}

	prompt_add_doctype() {
		if (!this.filters.role) {
			frappe.msgprint(__("Select a Role first."));
			return;
		}
		const existing = new Set(this.all_rows.map((r) => r.parent));
		let doctypes = (this.options.doctypes || []).map((d) => d.value);
		const finish = () => {
			doctypes = doctypes.filter((d) => !existing.has(d));
			const d = new frappe.ui.Dialog({
				title: __("Add DocType"),
				fields: [
					{
						fieldname: "doctype",
						label: __("Document Type"),
						fieldtype: "Autocomplete",
						options: doctypes,
						reqd: 1,
					},
					{
						fieldname: "permlevel",
						label: __("Permission Level"),
						fieldtype: "Int",
						default: 0,
					},
				],
				primary_action_label: __("Add"),
				primary_action: (values) => {
					d.hide();
					this.add_doctype(values.doctype, cint(values.permlevel) || 0);
				},
			});
			d.show();
		};

		if (this.filters.module) {
			this.api("get_doctypes_for_module", { module: this.filters.module })
				.then((r) => {
					doctypes = r.message || doctypes;
					finish();
				})
				.catch(() => finish());
		} else {
			finish();
		}
	}

	async add_doctype(doctype, permlevel) {
		try {
			await this.pm("add", {
				parent: doctype,
				role: this.filters.role,
				permlevel: permlevel,
			});
			frappe.show_alert({ message: __("Permission added"), indicator: "green" });
			await this.load_matrix();
		} catch (e) {
			frappe.msgprint(__("Could not add permission."));
		}
	}

	remove_row(row) {
		frappe.confirm(__("Remove permissions for {0}?", [__(row.parent)]), async () => {
			try {
				await this.pm("remove", {
					doctype: row.parent,
					role: row.role,
					permlevel: row.permlevel,
					if_owner: row.if_owner,
				});
				frappe.show_alert({ message: __("Permission removed"), indicator: "green" });
				await this.load_matrix();
			} catch (e) {
				frappe.msgprint(__("Did not remove"));
			}
		});
	}
};
