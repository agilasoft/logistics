// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.provide("logistics.permission_studio");

logistics.permission_studio.PermissionStudioPage = class PermissionStudioPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Permission Studio"),
			single_column: true,
		});
		$(wrapper).find(".page-head").hide();
		this.$body = $(wrapper).find(".layout-main-section");
		this.section = (frappe.route_options && frappe.route_options.section) || "overview";
		this.filters = { search: "", status: "", category: "", sort: "modified", page: 1 };
		this.userFilters = { search: "", assignment: "all", page: 1 };
		if (frappe.route_options && frappe.route_options.assignment) {
			this.userFilters.assignment = frappe.route_options.assignment;
			this.section = "users";
		}
		this.selected = new Set();
		this.active = null;
		this.group = null;
		this.detailTab = "overview";
		this.settings = { list_page_size: 10, picker_page_size: 25 };
		this.picker = logistics.permission_studio_picker;
		frappe.route_options = null;
		this.render_shell();
		this.bind_shell();
		this.call("settings")
			.then((settings) => {
				this.settings = settings || this.settings;
				this.show(this.section);
			})
			.catch(() => this.show(this.section));
	}

	call(method, args) {
		return frappe
			.call({
				method: "logistics.logistics.page.permission_studio.permission_studio." + method,
				args: args || {},
			})
			.then((response) => response.message);
	}

	esc(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	}

	toast(message, indicator) {
		frappe.show_alert({ message: message, indicator: indicator || "green" });
	}

	fail(error, fallback) {
		const message =
			(error && (error.message || (error._server_messages && this.server_message(error)))) ||
			fallback ||
			__("The request failed.");
		frappe.msgprint({ title: __("Permission Studio"), message: message, indicator: "red" });
	}

	server_message(error) {
		try {
			const messages = JSON.parse(error._server_messages);
			return messages
				.map((item) => {
					try {
						return JSON.parse(item).message;
					} catch (e) {
						return item;
					}
				})
				.join(" ");
		} catch (e) {
			return "";
		}
	}

	confirm(message) {
		return new Promise((resolve) => {
			frappe.confirm(message, () => resolve(true), () => resolve(false));
		});
	}

	status_class(status) {
		return (
			{
				"In Sync": "is-sync",
				"Changes Pending": "is-pending",
				"Sync Failed": "is-failed",
				Syncing: "is-syncing",
			}[status] || ""
		);
	}

	render_shell() {
		const items = [
			["overview", __("Overview")],
			["groups", __("Permission Groups")],
			["users", __("Users")],
			["matrix", __("Permission Matrix")],
			["access", __("View User Access")],
			["templates", __("Templates")],
			["health", __("Health Check")],
			["activity", __("Activity")],
			["settings", __("Settings")],
		];
		this.$body.html(
			`<div class="ps-app">
				<aside class="ps-nav">
					<div class="ps-brand">
						<div class="ps-brand-mark">PS</div>
						<div>
							<div class="ps-brand-title">${__("Permission Studio")}</div>
							<div class="ps-brand-sub">${__("Groups, access, and sync")}</div>
						</div>
					</div>
					${items
						.map(
							(item) =>
								`<button type="button" class="ps-nav-item" data-section="${item[0]}">${item[1]}</button>`
						)
						.join("")}
					<div class="ps-nav-label">${__("Quick Actions")}</div>
					<button type="button" class="ps-quick-item" data-action="sync-all">${__("Sync All")}</button>
					<button type="button" class="ps-quick-item" data-action="create-group">${__("Create Group")}</button>
					<button type="button" class="ps-quick-item" data-action="bulk">${__("Bulk Actions")}</button>
				</aside>
				<section class="ps-main"></section>
			</div>`
		);
		this.$main = this.$body.find(".ps-main");
	}

	bind_shell() {
		this.$body.on("click", ".ps-nav-item", (event) => {
			this.show(event.currentTarget.getAttribute("data-section"));
		});
		this.$body.on("click", "[data-action='sync-all']", () => this.sync_groups(null));
		this.$body.on("click", "[data-action='create-group']", () => this.edit_group(null));
		this.$body.on("click", "[data-action='bulk']", () => this.bulk_menu());
	}

	show(section) {
		this.section = section || "overview";
		this.$body.find(".ps-nav-item").removeClass("active");
		this.$body.find(`.ps-nav-item[data-section="${this.section}"]`).addClass("active");
		const views = {
			overview: () => this.render_groups(true),
			groups: () => this.render_groups(false),
			users: () => this.render_users(),
			matrix: () => this.render_matrix(),
			access: () => this.render_access(),
			templates: () => this.render_templates(),
			health: () => this.render_health(),
			activity: () => this.render_activity(),
			settings: () => this.render_settings(),
		};
		(views[this.section] || views.overview)();
	}

	refresh() {
		this.show(this.section);
	}

	render_groups(with_cards) {
		this.$main.html(
			`${with_cards ? '<div class="ps-cards"></div>' : ""}
			<div class="ps-workspace">
				<div class="ps-panel ps-list-panel">
					<div class="ps-panel-head">
						<div>
							<div class="ps-panel-title">${__("Permission Groups")}</div>
							<div class="ps-panel-sub">${__("Manage and configure permission groups for your organization.")}</div>
						</div>
						<button type="button" class="btn btn-primary btn-sm ps-new-group">${__("New Group")}</button>
					</div>
					<div class="ps-toolbar">
						<input type="search" class="ps-search" placeholder="${__("Search groups...")}" value="${this.esc(this.filters.search)}">
						<select class="ps-category">
							<option value="">${__("All Groups")}</option>
							${["Accounting", "Sales", "Operations", "Management", "Custom"]
								.map(
									(category) =>
										`<option value="${category}" ${this.filters.category === category ? "selected" : ""}>${__(category)}</option>`
								)
								.join("")}
						</select>
						<select class="ps-status">
							<option value="">${__("All Statuses")}</option>
							${["In Sync", "Changes Pending", "Sync Failed", "Syncing"]
								.map(
									(status) =>
										`<option value="${status}" ${this.filters.status === status ? "selected" : ""}>${__(status)}</option>`
								)
								.join("")}
						</select>
					</div>
					<div class="ps-bulk" style="display:none"></div>
					<div class="ps-table-wrap"><div class="ps-loading">${__("Loading groups...")}</div></div>
					<div class="ps-footer"></div>
				</div>
				<div class="ps-panel ps-detail"><div class="ps-empty">${__("Select a permission group.")}</div></div>
			</div>`
		);
		if (with_cards) {
			this.load_cards();
		}
		this.$main.find(".ps-new-group").on("click", () => this.edit_group(null));
		this.$main.find(".ps-search").on("change", (event) => {
			this.filters.search = event.target.value;
			this.filters.page = 1;
			this.load_group_table();
		});
		this.$main.find(".ps-category, .ps-status").on("change", (event) => {
			const field = event.target.classList.contains("ps-category") ? "category" : "status";
			this.filters[field] = event.target.value;
			this.filters.page = 1;
			this.load_group_table();
		});
		this.load_group_table();
	}

	load_cards() {
		this.call("dashboard")
			.then((data) => {
				const icons = { groups: "G", users_in_groups: "U", users_without_groups: "W", managed_permissions: "P", issues: "!" };
				this.$main.find(".ps-cards").html(
					(data.cards || [])
						.map((card) => {
							const delta =
								card.delta == null
									? ""
									: `<div class="ps-card-delta ${card.delta > 0 ? "ps-delta-up" : card.delta < 0 ? "ps-delta-down" : ""}">${card.delta > 0 ? "↑" : card.delta < 0 ? "↓" : ""} ${Math.abs(card.delta)}</div>`;
							return `<button type="button" class="ps-card ${this.esc(card.key)}" data-target="${this.esc(card.target)}">
								<div class="ps-card-top"><span class="ps-card-icon">${icons[card.key] || ""}</span></div>
								<div class="ps-card-value">${this.esc(card.value)}</div>
								<div class="ps-card-label">${this.esc(card.label)}</div>
								${delta}
							</button>`;
						})
						.join("")
				);
				this.$main.find(".ps-card").on("click", (event) => {
					const target = event.currentTarget.getAttribute("data-target");
					if (target === "users") {
						this.userFilters.assignment = "grouped";
						this.show("users");
					} else if (target === "users_without") {
						this.userFilters.assignment = "ungrouped";
						this.show("users");
					} else if (target === "health") {
						this.show("health");
					} else {
						this.show("groups");
					}
				});
			})
			.catch((error) => this.fail(error, __("Dashboard figures could not be loaded.")));
	}

	load_group_table() {
		this.call("groups", {
			search: this.filters.search,
			status: this.filters.status,
			category: this.filters.category,
			sort: this.filters.sort,
			page: this.filters.page,
			page_size: this.settings.list_page_size,
		})
			.then((data) => {
				this.group_page = data;
				if (!(data.rows || []).length) {
					this.$main.find(".ps-table-wrap").html(
						`<div class="ps-empty">${__("No permission groups match these filters.")}</div>`
					);
				} else {
					this.$main.find(".ps-table-wrap").html(this.group_table(data.rows));
					this.bind_group_table();
				}
				this.$main.find(".ps-footer").html(
					`<span>${__("Showing {0}-{1} of {2} groups", [data.from || 0, data.to || 0, data.total || 0])}</span>
					<div class="ps-pager">
						<button type="button" class="btn btn-default btn-xs" data-page="${data.page - 1}" ${data.page <= 1 ? "disabled" : ""}>${__("Previous")}</button>
						<button type="button" class="btn btn-default btn-xs" data-page="${data.page + 1}" ${data.to >= data.total ? "disabled" : ""}>${__("Next")}</button>
					</div>`
				);
				this.$main.find(".ps-pager button").on("click", (event) => {
					this.filters.page = Number(event.currentTarget.getAttribute("data-page"));
					this.load_group_table();
				});
				this.render_bulk_bar();
				if (this.active) {
					this.open_group(this.active);
				}
			})
			.catch((error) => this.fail(error, __("Permission groups could not be loaded.")));
	}

	group_table(rows) {
		const headers = [
			["", ""],
			["group_name", __("Group Name")],
			["members", __("Members")],
			["", __("Permitted Values")],
			["", __("Status")],
			["modified", __("Last Modified")],
			["", __("Actions")],
		];
		return `<table class="ps-table">
			<thead><tr>
				${headers
					.map(
						(header) =>
							`<th>${header[0] ? `<button type="button" class="btn btn-link btn-xs ps-sort" data-sort="${header[0]}">${header[1]}</button>` : header[1]}</th>`
					)
					.join("")}
			</tr></thead>
			<tbody>
				${rows
					.map((row) => {
						const disabled = row.enabled ? "" : `<div class="ps-pill is-off">${__("Disabled")}</div>`;
						return `<tr class="${this.active === row.name ? "is-active" : ""}" data-group="${this.esc(row.name)}">
							<td><input type="checkbox" class="ps-select" data-group="${this.esc(row.name)}" ${this.selected.has(row.name) ? "checked" : ""}></td>
							<td>
								<div class="ps-group-name">
									<span class="ps-avatar" style="background:${this.esc(row.color || "#2563eb")}">${this.esc(row.abbreviation || "")}</span>
									<div>
										<div class="ps-strong">${this.esc(row.group_name || row.name)}</div>
										<div class="ps-muted">${this.esc(row.description || row.category || "")}</div>
									</div>
								</div>
							</td>
							<td>${this.esc(row.member_count || 0)}</td>
							<td>${this.esc(row.value_count || 0)}</td>
							<td><span class="ps-pill ${this.status_class(row.sync_status)}">${this.esc(row.sync_status || "")}</span> ${disabled}</td>
							<td>
								<div>${this.esc(frappe.datetime.str_to_user(row.modified) || row.modified || "")}</div>
								<div class="ps-muted">${this.esc(row.modified_by_name || "")}</div>
							</td>
							<td>
								<div class="ps-menu">
									<button type="button" class="btn btn-default btn-xs ps-row-menu" data-group="${this.esc(row.name)}">...</button>
								</div>
							</td>
						</tr>`;
					})
					.join("")}
			</tbody>
		</table>`;
	}

	bind_group_table() {
		this.$main.find(".ps-sort").on("click", (event) => {
			this.filters.sort = event.currentTarget.getAttribute("data-sort");
			this.load_group_table();
		});
		this.$main.find("tbody tr").on("click", (event) => {
			if ($(event.target).is("input, button")) {
				return;
			}
			this.open_group(event.currentTarget.getAttribute("data-group"));
		});
		this.$main.find(".ps-select").on("change", (event) => {
			const name = event.target.getAttribute("data-group");
			if (event.target.checked) {
				this.selected.add(name);
			} else {
				this.selected.delete(name);
			}
			this.render_bulk_bar();
		});
		this.$main.find(".ps-row-menu").on("click", (event) => {
			event.stopPropagation();
			this.open_row_menu(event.currentTarget);
		});
	}

	render_bulk_bar() {
		const bar = this.$main.find(".ps-bulk");
		if (!this.selected.size) {
			bar.hide().empty();
			return;
		}
		bar.show().html(
			`<span>${__("{0} selected", [this.selected.size])}</span>
			<button type="button" class="btn btn-default btn-xs" data-bulk="sync">${__("Sync Selected")}</button>
			<button type="button" class="btn btn-default btn-xs" data-bulk="export">${__("Export")}</button>
			<button type="button" class="btn btn-default btn-xs" data-bulk="copy">${__("Copy Values")}</button>`
		);
		bar.find("[data-bulk]").on("click", (event) => {
			const action = event.currentTarget.getAttribute("data-bulk");
			const names = Array.from(this.selected);
			if (action === "sync") {
				this.sync_groups(names);
			} else if (action === "export") {
				this.export_groups(names);
			} else {
				this.copy_values_dialog(names);
			}
		});
	}

	open_row_menu(button) {
		const name = button.getAttribute("data-group");
		$(".ps-menu-list").remove();
		const menu = $(
			`<div class="ps-menu-list">
				<button type="button" data-do="open">${__("Open")}</button>
				<button type="button" data-do="edit">${__("Edit Group")}</button>
				<button type="button" data-do="sync">${__("Sync")}</button>
				<button type="button" data-do="template">${__("Save as Template")}</button>
				<button type="button" data-do="disable">${__("Enable or Disable")}</button>
				<button type="button" data-do="delete">${__("Delete")}</button>
			</div>`
		);
		$(button).after(menu);
		menu.on("click", "button", async (event) => {
			const action = event.currentTarget.getAttribute("data-do");
			menu.remove();
			if (action === "open") {
				this.open_group(name);
			} else if (action === "edit") {
				const group = await this.call("group", { name });
				this.edit_group(group);
			} else if (action === "sync") {
				this.sync_groups([name]);
			} else if (action === "template") {
				this.save_template_from_group(name);
			} else if (action === "disable") {
				const group = await this.call("group", { name });
				await this.call("enabled", { name, enabled: group.enabled ? 0 : 1 });
				this.toast(__("Group updated."));
				this.load_group_table();
			} else if (action === "delete") {
				this.delete_group(name);
			}
		});
	}

	open_group(name) {
		this.active = name;
		this.$main.find("tbody tr").removeClass("is-active");
		this.$main.find(`tr[data-group="${name}"]`).addClass("is-active");
		const detail = this.$main.find(".ps-detail");
		detail.html(`<div class="ps-loading">${__("Loading group...")}</div>`);
		this.call("group", { name })
			.then((group) => {
				this.group = group;
				this.render_detail(group);
			})
			.catch((error) => this.fail(error, __("The group could not be opened.")));
	}

	render_detail(group) {
		const summary = group.summary || {};
		const tabs = ["overview", "members", "permissions", "activity"];
		this.$main.find(".ps-detail").html(
			`<div class="ps-detail-hero">
				<div class="ps-group-name">
					<span class="ps-avatar" style="background:${this.esc(group.color || "#2563eb")}">${this.esc(group.abbreviation || "")}</span>
					<div>
						<div class="ps-panel-title">${this.esc(group.group_name)}</div>
						<div class="ps-muted">${this.esc(group.description || "")}</div>
					</div>
				</div>
				<div class="ps-actions">
					<span class="ps-pill ${this.status_class(group.sync_status)}">${this.esc(group.sync_status || "")}</span>
					<button type="button" class="btn btn-default btn-sm ps-edit">${__("Edit Group")}</button>
				</div>
			</div>
			<div class="ps-tabs">
				${tabs
					.map((tab) => {
						const labels = {
							overview: __("Overview"),
							members: __("Members"),
							permissions: __("Permissions"),
							activity: __("Activity"),
						};
						return `<button type="button" class="ps-tab ${this.detailTab === tab ? "active" : ""}" data-tab="${tab}">${labels[tab]}</button>`;
					})
					.join("")}
			</div>
			<div class="ps-detail-body"></div>`
		);
		const body = this.$main.find(".ps-detail-body");
		if (this.detailTab === "members") {
			body.html(this.member_tab(group));
		} else if (this.detailTab === "permissions") {
			body.html(this.permission_tab(group));
		} else if (this.detailTab === "activity") {
			body.html(this.activity_tab(group.activity || []));
		} else {
			body.html(this.overview_tab(group, summary));
		}
		this.$main.find(".ps-tab").on("click", (event) => {
			this.detailTab = event.currentTarget.getAttribute("data-tab");
			this.render_detail(group);
		});
		this.$main.find(".ps-edit").on("click", () => this.edit_group(group));
		this.bind_detail_actions(group);
	}

	overview_tab(group, summary) {
		const fields = Object.keys(summary.fields || {})
			.map((field) => `<div>${this.esc(field)}: ${this.esc(summary.fields[field])}</div>`)
			.join("");
		return `<div class="ps-kv">
				<div class="ps-muted">${__("Group Name")}</div><div>${this.esc(group.group_name)}</div>
				<div class="ps-muted">${__("Description")}</div><div>${this.esc(group.description || "—")}</div>
				<div class="ps-muted">${__("Enabled")}</div><div>${group.enabled ? __("Yes") : __("No")}</div>
				<div class="ps-muted">${__("Created")}</div><div>${this.esc(frappe.datetime.str_to_user(group.creation) || "")}</div>
				<div class="ps-muted">${__("Last Modified")}</div><div>${this.esc(frappe.datetime.str_to_user(group.modified) || "")}</div>
			</div>
			<div class="ps-split">
				<div class="ps-subcard"><h4>${__("Members")}</h4>${this.people_list((group.members || []).slice(0, 5))}</div>
				<div class="ps-subcard"><h4>${__("Permitted Values")}</h4>${this.value_list((group.permitted_values || []).slice(0, 5))}</div>
			</div>
			<div class="ps-summary">
				<div class="ps-strong">${__("Group Access Summary")}</div>
				<div>${__("{0} members", [summary.members || 0])}</div>
				<div>${__("{0} permitted values", [summary.permitted_values || 0])}</div>
				<div>${__("{0} applicable document types", [(summary.applicable_doctypes || []).length])}</div>
				${fields}
				<div class="ps-note">${this.esc(summary.note || "")}</div>
			</div>`;
	}

	member_tab(group) {
		return `<div class="ps-actions" style="margin-bottom:8px">
				<input type="search" class="ps-member-search" placeholder="${__("Search members")}">
				<button type="button" class="btn btn-primary btn-sm ps-add-members">${__("Add Users")}</button>
				<button type="button" class="btn btn-default btn-sm ps-remove-members">${__("Remove Selected")}</button>
			</div>
			<div class="ps-member-list">${this.people_list(group.members || [], true)}</div>`;
	}

	permission_tab(group) {
		return `<div class="ps-actions" style="margin-bottom:8px">
				<input type="search" class="ps-value-search" placeholder="${__("Search permitted values")}">
				<select class="ps-value-filter"><option value="">${__("All fields")}</option></select>
				<button type="button" class="btn btn-primary btn-sm ps-add-values">${__("Add Values")}</button>
				<button type="button" class="btn btn-default btn-sm ps-remove-values">${__("Remove Selected")}</button>
			</div>
			<div class="ps-note">${__("These rows are User Permission restrictions. They do not grant role access to the document type.")}</div>
			<div class="ps-value-list">${this.value_list(group.permitted_values || [], true)}</div>`;
	}

	activity_tab(rows) {
		if (!rows.length) {
			return `<div class="ps-empty">${__("No activity for this group yet.")}</div>`;
		}
		return rows
			.map(
				(row) => `<div class="ps-activity">
					<div>
						<div class="ps-strong">${this.esc(row.action)}</div>
						<div class="ps-muted">${this.esc(row.actor || row.owner || "")} · ${this.esc(row.creation || "")}</div>
						<div>${this.esc(row.details || row.affected_record || "")}</div>
					</div>
					<span class="ps-pill ${row.result === "Failed" ? "is-failed" : "is-sync"}">${this.esc(row.result || "")}</span>
				</div>`
			)
			.join("");
	}

	people_list(members, selectable) {
		if (!members.length) {
			return `<div class="ps-empty">${__("No users are assigned.")}</div>`;
		}
		return members
			.map((member) => {
				const enabled = member.enabled ? __("Enabled") : __("Disabled");
				return `<label class="ps-person">
					<span>${selectable ? `<input type="checkbox" class="ps-member-check" data-user="${this.esc(member.user)}"> ` : ""}
						<span class="ps-strong">${this.esc(member.full_name || member.user)}</span>
						<span class="ps-muted"> ${this.esc(member.email || member.user)} · ${enabled}</span>
					</span>
					${selectable ? `<button type="button" class="btn btn-link btn-xs ps-remove-member" data-user="${this.esc(member.user)}">${__("Remove")}</button>` : ""}
				</label>`;
			})
			.join("");
	}

	value_list(values, selectable) {
		if (!values.length) {
			return `<div class="ps-empty">${__("No permitted values.")}</div>`;
		}
		return values
			.map((value) => {
				const scope = value.applicable_for
					? __("only {0}", [value.applicable_for])
					: __("all document types");
				return `<label class="ps-value">
					<span>${selectable ? `<input type="checkbox" class="ps-value-check" data-key="${this.esc(this.value_key(value))}"> ` : ""}
						<span class="ps-strong">${this.esc(value.allow)}</span>
						<div>${this.esc(value.for_value)}</div>
						<div class="ps-muted">${this.esc(scope)}</div>
					</span>
				</label>`;
			})
			.join("");
	}

	value_key(value) {
		return [value.allow, value.for_value, value.applicable_for || ""].join("|");
	}

	bind_detail_actions(group) {
		this.$main.find(".ps-member-search").on("input", (event) => {
			const query = event.target.value.toLowerCase();
			const rows = (group.members || []).filter((member) =>
				`${member.full_name} ${member.user} ${member.email}`.toLowerCase().includes(query)
			);
			this.$main.find(".ps-member-list").html(this.people_list(rows, true));
			this.bind_member_buttons(group);
		});
		this.$main.find(".ps-value-search").on("input", () => this.filter_values(group));
		const fields = Array.from(new Set((group.permitted_values || []).map((value) => value.allow))).sort();
		this.$main.find(".ps-value-filter").append(
			fields.map((field) => `<option value="${this.esc(field)}">${this.esc(field)}</option>`).join("")
		);
		this.$main.find(".ps-value-filter").on("change", () => this.filter_values(group));
		this.$main.find(".ps-add-members").on("click", () => this.add_members(group));
		this.$main.find(".ps-add-values").on("click", () => this.add_values(group));
		this.$main.find(".ps-remove-members").on("click", () => this.remove_selected_members(group));
		this.$main.find(".ps-remove-values").on("click", () => this.remove_selected_values(group));
		this.bind_member_buttons(group);
	}

	bind_member_buttons(group) {
		this.$main.find(".ps-remove-member").on("click", async (event) => {
			const user = event.currentTarget.getAttribute("data-user");
			if (!(await this.confirm(__("Remove {0} from {1}?", [user, group.group_name])))) {
				return;
			}
			this.apply_members(group, (group.members || []).filter((member) => member.user !== user).map((member) => member.user));
		});
	}

	filter_values(group) {
		const query = (this.$main.find(".ps-value-search").val() || "").toLowerCase();
		const field = this.$main.find(".ps-value-filter").val() || "";
		const rows = (group.permitted_values || []).filter((value) => {
			const hay = `${value.allow} ${value.for_value} ${value.applicable_for}`.toLowerCase();
			return (!field || value.allow === field) && (!query || hay.includes(query));
		});
		this.$main.find(".ps-value-list").html(this.value_list(rows, true));
	}

	edit_group(group) {
		const dialog = new frappe.ui.Dialog({
			title: group ? __("Edit Group") : __("New Group"),
			fields: [
				{
					fieldname: "group_name",
					fieldtype: "Data",
					label: __("Group Name"),
					reqd: !group,
					read_only: group ? 1 : 0,
					default: group ? group.group_name : "",
				},
				{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: group ? group.description : "" },
				{
					fieldname: "category",
					fieldtype: "Select",
					label: __("Category"),
					options: "\nAccounting\nSales\nOperations\nManagement\nCustom",
					default: group ? group.category : "",
				},
				{ fieldname: "abbreviation", fieldtype: "Data", label: __("Abbreviation"), default: group ? group.abbreviation : "" },
				{ fieldname: "color", fieldtype: "Data", label: __("Color"), default: group ? group.color : "" },
				{
					fieldname: "enabled",
					fieldtype: "Check",
					label: __("Enabled"),
					default: group ? group.enabled : 1,
				},
			],
			primary_action_label: __("Save"),
			primary_action: (values) => {
				const payload = Object.assign({}, values);
				if (group) {
					payload.name = group.name;
					payload.members = (group.members || []).map((member) => member.user);
					payload.permitted_values = group.permitted_values || [];
				}
				this.call("save", { payload })
					.then((saved) => {
						dialog.hide();
						this.toast(__("Group saved."));
						this.active = saved.name;
						this.show(this.section === "overview" ? "overview" : "groups");
					})
					.catch((error) => this.fail(error, __("The group could not be saved.")));
			},
		});
		dialog.show();
	}

	async delete_group(name) {
		if (!(await this.confirm(__("Delete this permission group and the User Permissions it owns?")))) {
			return;
		}
		this.call("delete", { name })
			.then(() => {
				this.toast(__("Group deleted."));
				this.active = null;
				this.selected.delete(name);
				this.load_group_table();
			})
			.catch((error) => this.fail(error, __("The group could not be deleted.")));
	}

	add_members(group) {
		this.open_picker({
			title: __("Add Users"),
			search_method: "user_search",
			allow_required: false,
			primary: __("Add Users"),
			on_submit: (selected) => {
				const users = selected.map((row) => row.name);
				this.preview_and_apply("add_members", { group: group.name, users }, () =>
					this.call("bulk_run", {
						operation: "add_members",
						payload: { group: group.name, users },
						confirmed: 1,
					}).then((result) => this.after_bulk(group.name, result))
				);
			},
		});
	}

	add_values(group) {
		this.open_picker({
			title: __("Add Permitted Values"),
			search_method: "documents",
			allow_required: true,
			primary: __("Add Selected"),
			on_submit: (selected, extra) => {
				const values = selected.map((row) => ({
					allow: extra.allow,
					for_value: row.name,
					applicable_for: extra.applicable_for || "",
				}));
				this.preview_and_apply("add_values", { group: group.name, values }, () =>
					this.call("bulk_run", {
						operation: "add_values",
						payload: { group: group.name, values },
						confirmed: 1,
					}).then((result) => this.after_bulk(group.name, result))
				);
			},
		});
	}

	apply_members(group, users) {
		return this.call("save", {
			payload: {
				name: group.name,
				members: users,
				permitted_values: group.permitted_values || [],
			},
		})
			.then(() => {
				this.toast(__("Members updated. Synchronize the group to write User Permissions."));
				this.open_group(group.name);
				this.load_group_table();
			})
			.catch((error) => this.fail(error, __("Members could not be updated.")));
	}

	apply_values(group, values) {
		return this.call("save", {
			payload: {
				name: group.name,
				members: (group.members || []).map((member) => member.user),
				permitted_values: values,
			},
		})
			.then(() => {
				this.toast(__("Permitted values updated. Synchronize the group to write User Permissions."));
				this.open_group(group.name);
				this.load_group_table();
			})
			.catch((error) => this.fail(error, __("Permitted values could not be updated.")));
	}

	async remove_selected_members(group) {
		const users = this.$main
			.find(".ps-member-check:checked")
			.toArray()
			.map((box) => box.getAttribute("data-user"));
		if (!users.length) {
			this.toast(__("Select members to remove."), "orange");
			return;
		}
		if (!(await this.confirm(__("Remove the selected members?")))) {
			return;
		}
		const preview = await this.call("bulk_plan", {
			operation: "remove_members",
			payload: { group: group.name, users },
		});
		this.show_plan(__("Remove Members"), preview, () =>
			this.apply_members(
				group,
				(group.members || []).map((member) => member.user).filter((user) => users.indexOf(user) === -1)
			)
		);
	}

	async remove_selected_values(group) {
		const keys = this.$main
			.find(".ps-value-check:checked")
			.toArray()
			.map((box) => box.getAttribute("data-key"));
		if (!keys.length) {
			this.toast(__("Select permitted values to remove."), "orange");
			return;
		}
		if (!(await this.confirm(__("Remove the selected permitted values?")))) {
			return;
		}
		const remaining = (group.permitted_values || []).filter((value) => keys.indexOf(this.value_key(value)) === -1);
		this.apply_values(group, remaining);
	}

	preview_and_apply(operation, payload, apply) {
		this.call("bulk_plan", { operation, payload })
			.then((preview) => this.show_plan(__("Review Changes"), preview, apply))
			.catch((error) => this.fail(error, __("The preview could not be built.")));
	}

	after_bulk(group, result) {
		const errors = result.errors || [];
		if (errors.length) {
			frappe.msgprint({
				title: __("Some records were not changed"),
				indicator: "orange",
				message: errors
					.map((item) => this.esc(item.record || item) + ": " + this.esc(item.error || ""))
					.join("<br>"),
			});
		} else {
			this.toast(__("Changes saved. Synchronize the group to write User Permissions."));
		}
		this.open_group(group);
		this.load_group_table();
	}

	show_plan(title, preview, apply) {
		const dialog = new frappe.ui.Dialog({
			title: title,
			fields: [{ fieldname: "plan", fieldtype: "HTML" }],
			primary_action_label: __("Confirm"),
			primary_action: () => {
				dialog.hide();
				apply();
			},
		});
		dialog.fields_dict.plan.$wrapper.html(
			`<pre class="ps-note">${this.esc(JSON.stringify(preview.preview || preview, null, 2))}</pre>`
		);
		dialog.show();
	}

	open_picker(options) {
		const picker = this.picker;
		const pageSize = this.settings.picker_page_size || picker.PICKER_PAGE_SIZE;
		const state = {
			allow: "",
			query: "",
			start: 0,
			documents: [],
			tagged: [],
			selected: [],
			loading: false,
			done: false,
			pageSize: pageSize,
		};
		const fields = [];
		if (options.allow_required) {
			fields.push({
				fieldname: "allow",
				fieldtype: "Link",
				options: "DocType",
				label: __("Document Type"),
				reqd: 1,
			});
		} else {
			fields.push({
				fieldname: "intro",
				fieldtype: "HTML",
				options: `<div class="ps-muted">${__("Search users, check the ones to add, then clear the search without losing the check.")}</div>`,
			});
		}
		fields.push(
			{ fieldname: "search", fieldtype: "Data", label: __("Search") },
			{ fieldname: "documents", fieldtype: "HTML" }
		);
		if (options.allow_required) {
			fields.push({
				fieldname: "applicable_for",
				fieldtype: "Link",
				options: "DocType",
				label: __("Applicable For"),
				description: __("Leave empty to apply this restriction on every document type that links to the value."),
			});
		}
		const dialog = new frappe.ui.Dialog({
			title: options.title,
			size: "large",
			fields: fields,
			primary_action_label: options.primary,
			primary_action: () => {
				if (options.allow_required && !state.allow) {
					frappe.msgprint(__("Select a document type."));
					return;
				}
				if (!state.selected.length) {
					frappe.msgprint(__("Select at least one row."));
					return;
				}
				dialog.hide();
				options.on_submit(state.selected.slice(), {
					allow: state.allow,
					applicable_for: dialog.get_value("applicable_for") || "",
				});
			},
		});
		dialog.show();
		const render = () => {
			const view = picker.pickerView({
				documents: state.documents,
				selected: state.selected,
				tagged: state.tagged,
				query: state.query,
				pageSize: state.pageSize,
			});
			const rows = view.rows
				.map((row) => {
					const tags = (row.tags || [])
						.map((tag) => {
							const parts = [tag.applicable_for, tag.group || tag.template, tag.source]
								.filter(Boolean)
								.filter((part, index, list) => list.indexOf(part) === index);
							return parts.length ? `<span class="ps-tag">${__("Tagged")} · ${this.esc(parts.join(" · "))}</span>` : "";
						})
						.join("");
					return `<label class="ps-doc-row">
						<input type="checkbox" class="ps-doc-check" data-name="${this.esc(row.name)}" ${row.checked ? "checked" : ""}>
						<span class="ps-doc-copy">
							<span class="ps-doc-label">${this.esc(row.label || row.name)}</span>
							${row.description ? `<div class="ps-muted">${this.esc(row.description)}</div>` : ""}
							${tags}
						</span>
					</label>`;
				})
				.join("");
			dialog.fields_dict.documents.$wrapper.html(
				`<div class="ps-doc-meta"><span>${__("{0} selected", [view.selectedCount])}</span><span>${state.loading ? __("Loading...") : __("{0} shown", [view.total])}</span></div>
				<div class="ps-doc-list" style="max-height:min(${view.viewportRows * 36}px, 60vh)">${rows || `<div class="ps-empty">${__("No documents.")}</div>`}</div>`
			);
			const list = dialog.fields_dict.documents.$wrapper.find(".ps-doc-list");
			list.on("scroll", () => {
				if (state.loading || state.done) {
					return;
				}
				if (list.scrollTop() + list.innerHeight() + 24 >= list[0].scrollHeight) {
					state.start += state.pageSize;
					load(false);
				}
			});
			list.on("change", ".ps-doc-check", (event) => {
				const name = event.target.getAttribute("data-name");
				const doc = view.rows.find((row) => row.name === name) || { name: name, label: name, tags: [] };
				state.selected = picker.toggleSelected(state.selected, doc, event.target.checked);
				const scroll = list.scrollTop();
				render();
				dialog.fields_dict.documents.$wrapper.find(".ps-doc-list").scrollTop(scroll);
			});
		};
		const load = (resetTagged) => {
			if (options.allow_required && !state.allow) {
				dialog.fields_dict.documents.$wrapper.html(
					`<div class="ps-empty">${__("Select a document type to list its records.")}</div>`
				);
				return;
			}
			state.loading = true;
			state.requestId = (state.requestId || 0) + 1;
			const requestId = state.requestId;
			render();
			const args = options.allow_required
				? {
						allow: state.allow,
						txt: state.query,
						start: state.start,
						page_len: state.pageSize,
						include_tagged: resetTagged ? 1 : 0,
				  }
				: { txt: state.query, start: state.start, page_len: state.pageSize };
			this.call(options.search_method, args)
				.then((result) => {
					if (requestId !== state.requestId) {
						return;
					}
					const incoming = result.documents || [];
					if (state.start === 0) {
						state.documents = incoming;
					} else {
						const seen = {};
						state.documents.forEach((row) => {
							seen[row.name] = true;
						});
						incoming.forEach((row) => {
							if (!seen[row.name]) {
								state.documents.push(row);
							}
						});
					}
					if (resetTagged) {
						state.tagged = result.tagged || [];
					}
					state.done = incoming.length < state.pageSize;
					state.pageSize = result.page_size || state.pageSize;
					state.loading = false;
					render();
				})
				.catch((error) => {
					if (requestId !== state.requestId) {
						return;
					}
					state.loading = false;
					this.fail(error, __("The document list could not be loaded."));
				});
		};
		if (options.allow_required) {
			dialog.fields_dict.allow.$input.on("change", () => {
				state.allow = dialog.get_value("allow") || "";
				state.start = 0;
				state.documents = [];
				state.tagged = [];
				state.selected = [];
				state.done = false;
				load(true);
			});
		} else {
			load(true);
		}
		dialog.fields_dict.search.$input.on("input", () => {
			state.query = dialog.get_value("search") || "";
			state.start = 0;
			state.done = false;
			load(false);
		});
		render();
	}

	sync_groups(names) {
		this.call("sync_preview", { names })
			.then((preview) => {
				const dialog = new frappe.ui.Dialog({
					title: __("Synchronization Preview"),
					fields: [{ fieldname: "body", fieldtype: "HTML" }],
					primary_action_label: __("Synchronize"),
					primary_action: () => {
						dialog.hide();
						this.call("sync", { names })
							.then((result) => {
								if (result.ok) {
									this.toast(__("Synchronization finished."));
								} else {
									frappe.msgprint({
										title: __("Synchronization failed"),
										message: __("Some groups did not synchronize: {0}", [(result.failed || []).join(", ")]),
										indicator: "red",
									});
								}
								this.load_group_table();
							})
							.catch((error) => this.fail(error, __("Synchronization failed.")));
					},
				});
				const lines = (preview.groups || [])
					.map(
						(group) =>
							`<div class="ps-person"><span>${this.esc(group.group)}</span><span>${__("Create {0}, update {1}, remove {2}", [group.create, group.update, group.remove])}</span></div>`
					)
					.join("");
				dialog.fields_dict.body.$wrapper.html(
					`<div>${__("Users affected")}: ${this.esc((preview.users || []).join(", ") || __("None"))}</div>${lines}
					<div class="ps-note">${__("Only User Permissions owned by Permission Studio are created, updated, or removed. Manual User Permissions stay in place.")}</div>`
				);
				dialog.show();
			})
			.catch((error) => this.fail(error, __("The synchronization preview could not be built.")));
	}

	export_groups(names) {
		this.call("export", { names })
			.then((data) => this.download("permission-groups.json", JSON.stringify(data.groups || [], null, 2), "application/json"))
			.catch((error) => this.fail(error, __("Export failed.")));
	}

	download(filename, text, type) {
		const blob = new Blob([text], { type: type || "text/plain" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = filename;
		link.click();
		URL.revokeObjectURL(url);
	}

	copy_values_dialog(names) {
		if (names.length < 1) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Copy Permitted Values"),
			fields: [
				{ fieldname: "source", fieldtype: "Link", options: "Permission Group", label: __("Source Group"), reqd: 1, default: names[0] },
				{ fieldname: "targets", fieldtype: "Small Text", label: __("Target Groups"), description: __("One group name per line."), default: names.slice(1).join("\n") },
			],
			primary_action_label: __("Preview"),
			primary_action: (values) => {
				const targets = (values.targets || "").split(/\n+/).map((name) => name.trim()).filter(Boolean);
				this.preview_and_apply("copy_values", { source: values.source, targets }, () =>
					this.call("bulk_run", { operation: "copy_values", payload: { source: values.source, targets }, confirmed: 1 }).then(
						(result) => {
							this.toast(__("Copy finished."));
							if (result.errors && result.errors.length) {
								frappe.msgprint(result.errors.map((item) => item.error).join("<br>"));
							}
							this.load_group_table();
						}
					)
				);
				dialog.hide();
			},
		});
		dialog.show();
	}

	bulk_menu() {
		const names = Array.from(this.selected);
		const dialog = new frappe.ui.Dialog({
			title: __("Bulk Actions"),
			fields: [
				{
					fieldname: "operation",
					fieldtype: "Select",
					label: __("Operation"),
					options: "sync\nexport\ncopy_values",
					default: "sync",
				},
			],
			primary_action_label: __("Continue"),
			primary_action: (values) => {
				dialog.hide();
				if (!names.length && values.operation !== "sync") {
					this.toast(__("Select groups in the list first."), "orange");
					return;
				}
				if (values.operation === "sync") {
					this.sync_groups(names.length ? names : null);
				} else if (values.operation === "export") {
					this.export_groups(names);
				} else {
					this.copy_values_dialog(names);
				}
			},
		});
		dialog.show();
	}

	save_template_from_group(name) {
		const dialog = new frappe.ui.Dialog({
			title: __("Save as Template"),
			fields: [{ fieldname: "template_name", fieldtype: "Data", label: __("Template Name"), reqd: 1 }],
			primary_action: (values) => {
				this.call("group_to_template", { group: name, template_name: values.template_name })
					.then(() => {
						dialog.hide();
						this.toast(__("Template saved. Members were not copied."));
					})
					.catch((error) => this.fail(error, __("The template could not be saved.")));
			},
		});
		dialog.show();
	}

	render_users() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head">
					<div>
						<div class="ps-panel-title">${__("Users")}</div>
						<div class="ps-panel-sub">${__("Group assignments and User Permissions.")}</div>
					</div>
				</div>
				<div class="ps-toolbar">
					<input type="search" class="ps-user-search" placeholder="${__("Search users")}" value="${this.esc(this.userFilters.search)}">
					<select class="ps-user-assignment">
						${[
							["all", __("All Users")],
							["grouped", __("In a Group")],
							["ungrouped", __("Without a Group")],
						]
							.map(
								(option) =>
									`<option value="${option[0]}" ${this.userFilters.assignment === option[0] ? "selected" : ""}>${option[1]}</option>`
							)
							.join("")}
					</select>
				</div>
				<div class="ps-user-body"><div class="ps-loading">${__("Loading users...")}</div></div>
			</div>`
		);
		const load = () => {
			this.call("users", this.userFilters)
				.then((data) => {
					if (!(data.rows || []).length) {
						this.$main.find(".ps-user-body").html(`<div class="ps-empty">${__("No users match this filter.")}</div>`);
						return;
					}
					this.$main.find(".ps-user-body").html(
						`<table class="ps-table"><thead><tr>
							<th>${__("User")}</th><th>${__("Status")}</th><th>${__("Groups")}</th><th>${__("Direct")}</th><th>${__("From Groups")}</th>
						</tr></thead><tbody>
						${data.rows
							.map(
								(row) => `<tr>
									<td><div class="ps-strong">${this.esc(row.full_name || row.name)}</div><div class="ps-muted">${this.esc(row.email || row.name)}</div></td>
									<td>${row.enabled ? __("Enabled") : __("Disabled")}</td>
									<td>${this.esc((row.groups || []).join(", ") || "—")}</td>
									<td>${this.esc(row.direct_permissions || 0)}</td>
									<td>${this.esc(row.managed_permissions || 0)}</td>
								</tr>`
							)
							.join("")}
						</tbody></table>`
					);
				})
				.catch((error) => this.fail(error, __("Users could not be loaded.")));
		};
		this.$main.find(".ps-user-search").on("change", (event) => {
			this.userFilters.search = event.target.value;
			load();
		});
		this.$main.find(".ps-user-assignment").on("change", (event) => {
			this.userFilters.assignment = event.target.value;
			load();
		});
		load();
	}

	render_matrix() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("Permission Matrix")}</div>
					<div class="ps-panel-sub">${__("Compare restriction configuration. A configured cell is not a role grant.")}</div></div>
					<button type="button" class="btn btn-default btn-sm ps-matrix-export">${__("Export")}</button>
				</div>
				<div class="ps-toolbar">
					<input class="ps-matrix-groups" placeholder="${__("Group names, comma separated")}">
					<input class="ps-matrix-field" placeholder="${__("Permission field")}">
					<input class="ps-matrix-applicable" placeholder="${__("Applicable document type")}">
					<input class="ps-matrix-search" placeholder="${__("Search values")}">
					<button type="button" class="btn btn-primary btn-sm ps-matrix-run">${__("Compare")}</button>
				</div>
				<div class="ps-matrix-body"><div class="ps-empty">${__("Choose groups to compare.")}</div></div>
			</div>`
		);
		const run = () => {
			const names = (this.$main.find(".ps-matrix-groups").val() || "")
				.split(",")
				.map((name) => name.trim())
				.filter(Boolean);
			this.call("matrix", {
				groups: names,
				field: this.$main.find(".ps-matrix-field").val(),
				applicable: this.$main.find(".ps-matrix-applicable").val(),
				search: this.$main.find(".ps-matrix-search").val(),
			})
				.then((matrix) => {
					this.matrix = matrix;
					if (!(matrix.rows || []).length) {
						this.$main.find(".ps-matrix-body").html(`<div class="ps-empty">${__("Nothing to compare.")}</div>`);
						return;
					}
					this.$main.find(".ps-matrix-body").html(
						`<div class="ps-note">${this.esc(matrix.note || "")}</div>
						<div class="ps-matrix-wrap"><table class="ps-table ps-matrix"><thead><tr><th>${__("Permission Field")}</th>
							${(matrix.columns || []).map((column) => `<th>${this.esc(column)}</th>`).join("")}
						</tr></thead><tbody>
							${matrix.rows
								.map(
									(row) => `<tr class="${row.different ? "is-diff" : ""}"><td>${this.esc(row.field)}</td>
										${(matrix.columns || [])
											.map((column) => {
												const cell = row.cells[column] || {};
												const label = cell.configured ? __("Configured") : __("Not Configured");
												return `<td><button type="button" class="linkish ps-cell" data-field="${this.esc(row.field)}" data-group="${this.esc(column)}">${label}</button></td>`;
											})
											.join("")}
									</tr>`
								)
								.join("")}
						</tbody></table></div>`
					);
					this.$main.find(".ps-cell").on("click", (event) => {
						const field = event.currentTarget.getAttribute("data-field");
						const group = event.currentTarget.getAttribute("data-group");
						const row = (matrix.rows || []).find((item) => item.field === field);
						const values = (row && row.cells[group] && row.cells[group].values) || [];
						frappe.msgprint({
							title: `${field} · ${group}`,
							message: values.length
								? values
										.map(
											(value) =>
												`${frappe.utils.escape_html(value.for_value)} · ${frappe.utils.escape_html(value.applicable_for || __("all document types"))}`
										)
										.join("<br>")
								: __("Not configured"),
						});
					});
				})
				.catch((error) => this.fail(error, __("The matrix could not be loaded.")));
		};
		this.$main.find(".ps-matrix-run").on("click", run);
		this.$main.find(".ps-matrix-export").on("click", () => {
			if (!this.matrix) {
				return;
			}
			const header = ["Permission Field"].concat(this.matrix.columns || []);
			const lines = [header.join(",")];
			(this.matrix.rows || []).forEach((row) => {
				lines.push(
					[row.field]
						.concat(
							(this.matrix.columns || []).map((column) =>
								row.cells[column] && row.cells[column].configured ? "Configured" : "Not Configured"
							)
						)
						.join(",")
				);
			});
			this.download("permission-matrix.csv", lines.join("\n"), "text/csv");
		});
	}

	render_access() {
		const actions = (frappe.perm && frappe.perm.rights ? frappe.perm.rights : ["read", "write", "create", "delete"]).filter(
			(right) => right !== "mask"
		);
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("View User Access")}</div>
					<div class="ps-panel-sub">${__("Inspect restrictions and ask Frappe whether an action is allowed.")}</div></div></div>
				<div class="ps-toolbar">
					<div class="ps-field" data-field="user"></div>
					<button type="button" class="btn btn-default btn-sm ps-load-user">${__("Show Access")}</button>
				</div>
				<div class="ps-access-body"></div>
				<div class="ps-panel-head"><div class="ps-panel-title">${__("Access Troubleshooter")}</div></div>
				<div class="ps-toolbar ps-check-fields">
					<div class="ps-field" data-field="doctype"></div>
					<div class="ps-field" data-field="document"></div>
					<select class="ps-action">${actions.map((action) => `<option value="${this.esc(action)}">${this.esc(action)}</option>`).join("")}</select>
					<button type="button" class="btn btn-primary btn-sm ps-check">${__("Check Access")}</button>
				</div>
				<div class="ps-check-body"></div>
			</div>`
		);
		this.access_user = frappe.ui.form.make_control({
			parent: this.$main.find('[data-field="user"]'),
			df: { fieldtype: "Link", options: "User", label: __("User"), fieldname: "user" },
			render_input: true,
		});
		this.access_doctype = frappe.ui.form.make_control({
			parent: this.$main.find('[data-field="doctype"]'),
			df: { fieldtype: "Link", options: "DocType", label: __("Document Type"), fieldname: "doctype" },
			render_input: true,
		});
		this.access_document = frappe.ui.form.make_control({
			parent: this.$main.find('[data-field="document"]'),
			df: {
				fieldtype: "Link",
				options: "DocType",
				label: __("Document"),
				fieldname: "document",
			},
			render_input: true,
		});
		this.access_doctype.df.change = () => {
			const doctype = this.access_doctype.get_value();
			if (doctype && this.access_document.df.options !== doctype) {
				this.access_document.df.options = doctype;
				this.access_document.set_value("");
				this.access_document.refresh();
			}
		};
		this.$main.find(".ps-load-user").on("click", () => this.load_user_access());
		this.$main.find(".ps-check").on("click", () => this.run_access_check());
	}

	load_user_access() {
		const user = this.access_user.get_value();
		if (!user) {
			return;
		}
		this.call("user_access", { user })
			.then((data) => {
				const summary = Object.keys(data.summary || {})
					.map((field) => {
						const lines = (data.summary[field] || [])
							.map(
								(row) =>
									`<div>${this.esc(field)} → ${this.esc(row.for_value)} → ${this.esc(row.source || __("Manual"))}</div>`
							)
							.join("");
						return `<div class="ps-subcard"><h4>${this.esc(field)}</h4>${lines}</div>`;
					})
					.join("");
				this.$main.find(".ps-access-body").html(
					`<div class="ps-kv">
						<div class="ps-muted">${__("Name")}</div><div>${this.esc(data.user.full_name || data.user.name)}</div>
						<div class="ps-muted">${__("Email")}</div><div>${this.esc(data.user.email || "")}</div>
						<div class="ps-muted">${__("Status")}</div><div>${data.user.enabled ? __("Enabled") : __("Disabled")}</div>
						<div class="ps-muted">${__("Roles")}</div><div>${this.esc((data.roles || []).join(", "))}</div>
						<div class="ps-muted">${__("Groups")}</div><div>${this.esc((data.groups || []).join(", ") || "—")}</div>
						<div class="ps-muted">${__("Direct User Permissions")}</div><div>${this.esc((data.direct || []).length)}</div>
						<div class="ps-muted">${__("Group-managed User Permissions")}</div><div>${this.esc((data.managed || []).length)}</div>
					</div>
					<div class="ps-note">${this.esc(data.note || "")}</div>
					<div class="ps-split">${summary || `<div class="ps-empty">${__("No User Permissions.")}</div>`}</div>`
				);
			})
			.catch((error) => this.fail(error, __("User access could not be loaded.")));
	}

	run_access_check() {
		const user = this.access_user.get_value();
		const doctype = this.access_doctype.get_value();
		if (!user || !doctype) {
			this.toast(__("Choose a user and a document type."), "orange");
			return;
		}
		this.call("access_check", {
			user,
			doctype,
			document: this.access_document.get_value() || "",
			action: this.$main.find(".ps-action").val(),
		})
			.then((result) => {
				const klass = result.allowed ? "ps-result-ok" : "ps-result-no";
				this.$main.find(".ps-check-body").html(
					`<div class="${klass}">${this.esc(result.status)}</div>
					<p>${this.esc(result.summary || "")}</p>
					<div class="ps-strong">${__("Evaluated")}</div>
					<ul>${(result.evaluated || []).map((line) => `<li>${this.esc(line)}</li>`).join("")}</ul>
					<div class="ps-strong">${__("Role permissions")}</div>
					<ul>${(result.role_permissions || [])
						.map(
							(row) =>
								`<li>${this.esc(row.role)} · ${row.granted ? __("grants this action") : __("does not grant this action")}</li>`
						)
						.join("")}</ul>
					<div class="ps-strong">${__("User Permission restrictions")}</div>
					<ul>${(result.user_permissions || [])
						.map(
							(row) =>
								`<li>${this.esc(row.allow)} → ${this.esc(row.for_value)} → ${this.esc(row.source)}${row.applicable_for ? " · " + this.esc(row.applicable_for) : ""}</li>`
						)
						.join("")}</ul>
					<div class="ps-strong">${__("Suggested actions")}</div>
					<ul>${(result.suggestions || []).map((line) => `<li>${this.esc(line)}</li>`).join("") || `<li>${__("None")}</li>`}</ul>`
				);
			})
			.catch((error) => this.fail(error, __("The access check failed.")));
	}

	render_templates() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("Templates")}</div>
					<div class="ps-panel-sub">${__("Reusable permitted values. Applying a template does not copy users.")}</div></div>
					<button type="button" class="btn btn-primary btn-sm ps-new-template">${__("New Template")}</button>
				</div>
				<div class="ps-template-body"><div class="ps-loading">${__("Loading templates...")}</div></div>
			</div>`
		);
		this.$main.find(".ps-new-template").on("click", () => this.edit_template(null));
		this.call("templates")
			.then((rows) => {
				if (!rows.length) {
					this.$main.find(".ps-template-body").html(`<div class="ps-empty">${__("No templates yet.")}</div>`);
					return;
				}
				this.$main.find(".ps-template-body").html(
					rows
						.map(
							(row) => `<div class="ps-person">
								<div><div class="ps-strong">${this.esc(row.template_name)}</div>
									<div class="ps-muted">${this.esc(row.category || "")} · ${__("{0} values", [(row.permitted_values || []).length])}</div>
									<div>${this.esc(row.description || "")}</div></div>
								<div class="ps-actions">
									<button type="button" class="btn btn-default btn-xs" data-template-edit="${this.esc(row.name)}">${__("Edit")}</button>
									<button type="button" class="btn btn-primary btn-xs" data-template-use="${this.esc(row.name)}">${__("Create Group")}</button>
									<button type="button" class="btn btn-default btn-xs" data-template-delete="${this.esc(row.name)}">${__("Delete")}</button>
								</div>
							</div>`
						)
						.join("")
				);
				this.templates = {};
				rows.forEach((row) => {
					this.templates[row.name] = row;
				});
				this.$main.find("[data-template-edit]").on("click", (event) => {
					this.edit_template(this.templates[event.currentTarget.getAttribute("data-template-edit")]);
				});
				this.$main.find("[data-template-use]").on("click", (event) => {
					this.use_template(this.templates[event.currentTarget.getAttribute("data-template-use")]);
				});
				this.$main.find("[data-template-delete]").on("click", async (event) => {
					const name = event.currentTarget.getAttribute("data-template-delete");
					if (!(await this.confirm(__("Delete this template?")))) {
						return;
					}
					this.call("delete_template_doc", { name }).then(() => this.render_templates());
				});
			})
			.catch((error) => this.fail(error, __("Templates could not be loaded.")));
	}

	edit_template(template) {
		const dialog = new frappe.ui.Dialog({
			title: template ? __("Edit Template") : __("New Template"),
			fields: [
				{ fieldname: "template_name", fieldtype: "Data", label: __("Template Name"), reqd: !template, read_only: template ? 1 : 0, default: template ? template.template_name : "" },
				{ fieldname: "category", fieldtype: "Select", label: __("Category"), options: "\nAccounting\nSales\nOperations\nManagement\nCustom", default: template ? template.category : "Custom" },
				{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: template ? template.description : "" },
			],
			primary_action: (values) => {
				const payload = Object.assign({}, values, {
					permitted_values: template ? template.permitted_values : [],
				});
				if (template) {
					payload.name = template.name;
				}
				this.call("save_template_doc", { payload })
					.then(() => {
						dialog.hide();
						this.render_templates();
					})
					.catch((error) => this.fail(error, __("The template could not be saved.")));
			},
		});
		dialog.show();
	}

	use_template(template) {
		const dialog = new frappe.ui.Dialog({
			title: __("Create Group from Template"),
			fields: [
				{ fieldname: "group_name", fieldtype: "Data", label: __("Group Name"), reqd: 1 },
				{
					fieldname: "review",
					fieldtype: "HTML",
					options: `<div class="ps-note">${(template.permitted_values || [])
						.map((value) => `${frappe.utils.escape_html(value.allow)} · ${frappe.utils.escape_html(value.for_value)} · ${frappe.utils.escape_html(value.applicable_for || __("all document types"))}`)
						.join("<br>")}</div>`,
				},
			],
			primary_action_label: __("Create Group"),
			primary_action: (values) => {
				this.call("template_to_group", {
					template: template.name,
					group_name: values.group_name,
					values: template.permitted_values || [],
					include_members: 0,
				})
					.then((group) => {
						dialog.hide();
						this.toast(__("Group created. Review it, then synchronize."));
						this.active = group.name;
						this.show("groups");
					})
					.catch((error) => this.fail(error, __("The group could not be created from this template.")));
			},
		});
		dialog.show();
	}

	render_health() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("Health Check")}</div>
					<div class="ps-panel-sub">${__("Read-only analysis. Nothing is changed until you choose an action.")}</div></div>
					<button type="button" class="btn btn-primary btn-sm ps-run-health">${__("Run Health Check")}</button>
				</div>
				<div class="ps-health-body"><div class="ps-empty">${__("Run a health check to look for permission issues.")}</div></div>
			</div>`
		);
		this.$main.find(".ps-run-health").on("click", () => {
			this.$main.find(".ps-health-body").html(`<div class="ps-loading">${__("Analyzing permissions...")}</div>`);
			this.call("health")
				.then((report) => this.draw_health(report))
				.catch((error) => this.fail(error, __("The health check failed.")));
		});
	}

	draw_health(report) {
		const counts = report.by_severity || {};
		const issues = (report.issues || [])
			.map((issue) => {
				const records = (issue.records || []).slice(0, 12);
				return `<div class="ps-issue">
					<div>
						<div class="ps-strong">${this.esc(issue.title)}</div>
						<div>${this.esc(issue.detail)}</div>
						<div class="ps-muted">${this.esc(records.map((record) => (typeof record === "string" ? record : JSON.stringify(record))).join(", "))}</div>
					</div>
					<div class="ps-actions">
						<span class="ps-pill ${issue.severity === "Critical" ? "is-failed" : issue.severity === "Warning" ? "is-pending" : "is-sync"}">${this.esc(issue.severity)}</span>
						${(issue.records || []).some((record) => typeof record === "string") ? `<button type="button" class="btn btn-default btn-xs ps-health-open" data-record="${this.esc((issue.records || []).find((record) => typeof record === "string") || "")}">${__("Open")}</button>` : ""}
						${issue.action === "sync" || issue.action === "retry" ? `<button type="button" class="btn btn-default btn-xs ps-health-sync" data-groups="${this.esc((issue.records || []).filter((record) => typeof record === "string").join(","))}">${__("Retry Sync")}</button>` : ""}
						${issue.action === "users" ? `<button type="button" class="btn btn-default btn-xs ps-health-users">${__("View Users")}</button>` : ""}
					</div>
				</div>`;
			})
			.join("");
		this.$main.find(".ps-health-body").html(
			`<div class="ps-cards">
				<div class="ps-card"><div class="ps-card-value">${this.esc(report.groups_analyzed || 0)}</div><div class="ps-card-label">${__("Groups analyzed")}</div></div>
				<div class="ps-card"><div class="ps-card-value">${this.esc(report.managed_checked || 0)}</div><div class="ps-card-label">${__("Managed permissions")}</div></div>
				<div class="ps-card"><div class="ps-card-value">${this.esc(report.issue_count || 0)}</div><div class="ps-card-label">${__("Issues")}</div></div>
				<div class="ps-card"><div class="ps-card-label">${__("Critical {0} · Warning {1} · Information {2}", [counts.Critical || 0, counts.Warning || 0, counts.Information || 0])}</div></div>
			</div>
			${issues || `<div class="ps-empty">${__("No issues detected.")}</div>`}`
		);
		this.$main.find(".ps-health-open").on("click", (event) => {
			const name = event.currentTarget.getAttribute("data-record");
			if (!name) {
				return;
			}
			this.active = name;
			this.show("groups");
		});
		this.$main.find(".ps-health-sync").on("click", (event) => {
			const groups = (event.currentTarget.getAttribute("data-groups") || "").split(",").filter(Boolean);
			this.sync_groups(groups);
		});
		this.$main.find(".ps-health-users").on("click", () => {
			this.userFilters.assignment = "ungrouped";
			this.show("users");
		});
	}

	render_activity() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("Activity")}</div></div>
					<button type="button" class="btn btn-default btn-sm ps-export-activity">${__("Export")}</button>
				</div>
				<div class="ps-toolbar">
					<input type="search" class="ps-activity-search" placeholder="${__("Search activity")}">
					<input class="ps-activity-action" placeholder="${__("Action")}">
					<input class="ps-activity-actor" placeholder="${__("Administrator")}">
					<input type="date" class="ps-activity-from">
					<input type="date" class="ps-activity-to">
					<button type="button" class="btn btn-primary btn-sm ps-activity-run">${__("Filter")}</button>
				</div>
				<div class="ps-activity-body"></div>
			</div>`
		);
		const load = () => {
			this.call("activity", {
				query: this.$main.find(".ps-activity-search").val(),
				action: this.$main.find(".ps-activity-action").val(),
				actor: this.$main.find(".ps-activity-actor").val(),
				date_from: this.$main.find(".ps-activity-from").val(),
				date_to: this.$main.find(".ps-activity-to").val(),
			})
				.then((rows) => {
					this.activity_rows = rows || [];
					if (!this.activity_rows.length) {
						this.$main.find(".ps-activity-body").html(`<div class="ps-empty">${__("No activity records.")}</div>`);
						return;
					}
					this.$main.find(".ps-activity-body").html(this.activity_tab(this.activity_rows));
				})
				.catch((error) => this.fail(error, __("Activity could not be loaded.")));
		};
		this.$main.find(".ps-activity-run").on("click", load);
		this.$main.find(".ps-export-activity").on("click", () => {
			const lines = [["Time", "Administrator", "Action", "Group", "Result", "Details"].join(",")];
			(this.activity_rows || []).forEach((row) => {
				lines.push(
					[row.creation, row.actor, row.action, row.permission_group, row.result, row.details]
						.map((value) => `"${String(value || "").replace(/"/g, '""')}"`)
						.join(",")
				);
			});
			this.download("permission-activity.csv", lines.join("\n"), "text/csv");
		});
		load();
	}

	render_settings() {
		this.$main.html(
			`<div class="ps-panel">
				<div class="ps-panel-head"><div><div class="ps-panel-title">${__("Settings")}</div>
					<div class="ps-panel-sub">${__("Permission Studio writes only the User Permissions it owns.")}</div></div></div>
				<div class="ps-detail-body ps-settings">
					<div class="ps-field"><label>${__("Groups per page")}</label><input type="number" class="ps-list-size" min="1" value="${this.esc(this.settings.list_page_size)}"></div>
					<div class="ps-field"><label>${__("Documents visible before scrolling")}</label><input type="number" class="ps-picker-size" min="1" value="${this.esc(this.settings.picker_page_size)}"></div>
					<button type="button" class="btn btn-primary btn-sm ps-save-settings">${__("Save")}</button>
				</div>
			</div>`
		);
		this.$main.find(".ps-save-settings").on("click", () => {
			this.call("save_studio_settings", {
				list_page_size: this.$main.find(".ps-list-size").val(),
				picker_page_size: this.$main.find(".ps-picker-size").val(),
			})
				.then((settings) => {
					this.settings = settings;
					this.toast(__("Settings saved."));
				})
				.catch((error) => this.fail(error, __("Settings could not be saved.")));
		});
	}
};
