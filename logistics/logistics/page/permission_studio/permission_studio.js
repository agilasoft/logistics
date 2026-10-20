// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

frappe.provide("frappehero");
if (!frappehero.call) {
	frappehero.esc = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	frappehero.initials = (label) =>
		String(label || "?")
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((part) => part.charAt(0).toUpperCase())
			.join("") || "?";
	frappehero.safe_color = (value) => (/^#[0-9a-fA-F]{6}$/.test(value || "") ? value : "#2490ef");
	frappehero.call = (method, args) => frappe.call({ method, args: args || {} }).then((response) => response.message);
}

frappe.pages["permission-studio"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Permission Studio"),
		single_column: true,
	});
	wrapper.studio = new frappehero.PermissionStudio(page, wrapper);
};

frappe.pages["permission-studio"].on_page_show = function (wrapper) {
	if (wrapper.studio) {
		wrapper.studio.show();
	}
};

frappehero.PermissionStudio = class PermissionStudio {
	constructor(page) {
		this.page = page;
		this.filters = { search: "", role: "", doctype: "", enabled: "all", conflicts_only: 0 };
		this.localQuery = "";
		this.selected = null;
		this.focusGroup = null;
		this.state = null;
		this.colors = ["#2490ef", "#5e64ff", "#db2777", "#d97706", "#16a34a", "#0891b2", "#7c3aed", "#dc2626"];
		this.page.main.addClass("fh-page");
		this.page.set_primary_action(__("New Group"), () => this.openGroupDialog(), "add");
		this.page.set_secondary_action(__("Sync All"), () => this.syncAll());
		this.page.add_menu_item(__("Permission Coverage"), () => {
			frappe.set_route("query-report", "Permission Coverage");
		});
		this.page.main.html(`
			<div class="fh-app">
				<div class="fh-stats"></div>
				<div class="fh-coverage fh-coverage-note"></div>
				<div class="fh-filters">
					<input type="search" class="fh-search" placeholder="${__("Search groups, users, values")}">
					<select class="fh-role"><option value="">${__("All roles")}</option></select>
					<select class="fh-doctype"><option value="">${__("All DocTypes")}</option></select>
					<select class="fh-enabled">
						<option value="all">${__("All groups")}</option>
						<option value="enabled">${__("Enabled")}</option>
						<option value="disabled">${__("Disabled")}</option>
					</select>
					<label class="fh-check"><input type="checkbox" class="fh-conflicts"> ${__("Conflicts only")}</label>
				</div>
				<div class="fh-banner" hidden></div>
				<div class="fh-body">
					<aside class="fh-list"></aside>
					<section class="fh-detail"></section>
				</div>
			</div>
		`);
		this.statsEl = this.page.main.find(".fh-stats");
		this.coverageEl = this.page.main.find(".fh-coverage-note");
		this.bannerEl = this.page.main.find(".fh-banner");
		this.listEl = this.page.main.find(".fh-list");
		this.detailEl = this.page.main.find(".fh-detail");
		const root = this.page.main.find(".fh-app").get(0);
		root.addEventListener("click", (event) => this.onClick(event));
		root.addEventListener("change", (event) => this.onChange(event));
		root.addEventListener("input", (event) => this.onInput(event));
		root.addEventListener("keydown", (event) => this.onKeydown(event));
		this.searchTimer = null;
	}

	show() {
		const routeName = frappe.get_route()[1];
		if (routeName) {
			this.focusGroup = decodeURIComponent(routeName);
		}
		this.refresh();
	}

	async refresh() {
		this.page.main.addClass("fh-loading");
		try {
			this.state = await frappehero.call("logistics.permission_studio.api.get_studio_state", {
				filters: this.filters,
			});
			if (this.focusGroup) {
				this.selected = this.focusGroup;
				this.focusGroup = null;
			}
			const names = (this.state.groups || []).map((group) => group.name);
			if (!names.includes(this.selected)) {
				this.selected = names[0] || null;
			}
			this.render();
		} finally {
			this.page.main.removeClass("fh-loading");
		}
	}

	render() {
		const stats = this.state.stats || {};
		const grouped = stats.grouped_users || 0;
		const ungrouped = stats.ungrouped_users || 0;
		const people = grouped + ungrouped || 1;
		this.statsEl.html(`
			<div class="fh-stat"><b>${stats.groups || 0}</b><span>${__("Groups")}</span></div>
			<div class="fh-stat"><b>${grouped}</b><span>${__("Users in a group")}</span></div>
			<div class="fh-stat"><b>${ungrouped}</b><span>${__("Users with no group")}</span></div>
			<div class="fh-stat"><b>${stats.grants || 0}</b><span>${__("User Permissions from groups")}</span></div>
		`);
		const messages = this.state.messages || [];
		if (messages.length) {
			this.bannerEl.removeAttr("hidden").html(messages.map((message) => `<div>${frappehero.esc(message)}</div>`).join(""));
		} else {
			this.bannerEl.attr("hidden", "hidden").empty();
		}
		this.fillSelect(".fh-role", (this.state.filter_options || {}).roles || [], __("All roles"));
		this.fillSelect(".fh-doctype", (this.state.filter_options || {}).doctypes || [], __("All DocTypes"));
		const percent = Math.round((grouped / people) * 100);
		this.coverageEl.html(`
			<div class="fh-bar"><i class="grouped" style="width:${percent}%"></i></div>
			<div class="fh-muted">${__("{0}% of enabled users are in a permission group", [String(percent)])}</div>
		`);
		this.renderList();
		this.renderDetail();
	}

	fillSelect(selector, values, placeholder) {
		const select = this.page.main.find(selector).get(0);
		const signature = values.join("|");
		if (select.dataset.signature === signature) {
			return;
		}
		const current = select.value;
		select.innerHTML =
			`<option value="">${frappehero.esc(placeholder)}</option>` +
			values.map((value) => `<option value="${frappehero.esc(value)}">${frappehero.esc(value)}</option>`).join("");
		select.dataset.signature = signature;
		if (values.includes(current)) {
			select.value = current;
		}
	}

	renderList() {
		const groups = this.state.groups || [];
		const cards = groups
			.map((group) => {
				const statusClass =
					group.sync_status === "Needs Attention"
						? "fh-pill-attention"
						: group.sync_status === "In Sync"
							? "fh-pill-sync"
							: "";
				const title = group.group_name || group.name;
				return `
					<button type="button" class="fh-card ${group.name === this.selected ? "fh-selected" : ""}" data-action="select-group" data-name="${frappehero.esc(group.name)}">
						<span class="fh-swatch" style="background:${frappehero.safe_color(group.color)}"></span>
						<span class="fh-card-text">
							<strong>${frappehero.esc(title)}</strong>
							<span class="fh-muted">${__("{0} members · {1} rules", [String(group.members.length), String(group.rules.length)])}</span>
						</span>
						<span class="fh-pill ${statusClass}">${frappehero.esc(group.enabled ? group.sync_status : __("Disabled"))}</span>
					</button>
				`;
			})
			.join("");
		const ungrouped = this.state.ungrouped_users || [];
		const extra =
			ungrouped.length || this.state.ungrouped_total
				? `
				<div class="fh-section-head">
					<strong>${__("No group")}</strong>
					<span class="fh-muted">${__("{0} shown of {1}", [
						String(ungrouped.length),
						String(this.state.ungrouped_total || ungrouped.length),
					])}</span>
				</div>
				${ungrouped
					.map(
						(user) => `
						<div class="fh-user-row">
							<span class="fh-avatar">${frappehero.esc(frappehero.initials(user.full_name || user.name))}</span>
							<span class="fh-card-text">
								<strong>${frappehero.esc(user.full_name || user.name)}</strong>
								<span class="fh-muted">${frappehero.esc(user.name)}</span>
							</span>
							<button type="button" class="fh-btn-quiet" data-action="add-ungrouped" data-user="${frappehero.esc(user.name)}">${__("Add")}</button>
						</div>`
					)
					.join("")}
			`
				: "";
		this.listEl.html(cards + extra || `<div class="fh-empty">${__("No groups match these filters.")}</div>`);
	}

	selectedGroup() {
		return (this.state.groups || []).find((group) => group.name === this.selected) || null;
	}

	localSlice(group) {
		const query = (this.localQuery || "").trim().toLowerCase();
		if (!query) {
			return { members: group.members, rules: group.rules };
		}
		const memberHit = (member) =>
			`${member.full_name} ${member.user} ${(member.roles || []).join(" ")}`.toLowerCase().includes(query);
		const ruleHit = (rule) =>
			`${rule.reference_doctype} ${rule.for_value} ${rule.applicable_for || ""}`.toLowerCase().includes(query);
		const members = group.members.filter(memberHit);
		const rules = group.rules.filter(ruleHit);
		return {
			members: members.length ? members : group.members,
			rules: rules.length ? rules : group.rules,
		};
	}

	renderDetail() {
		const group = this.selectedGroup();
		if (!group) {
			this.detailEl.html(`
				<div class="fh-empty">
					<p>${__("Create a group, add the people in it, then add the companies, territories, or other values they may use.")}</p>
					<button type="button" class="fh-btn" data-action="new-group">${__("New Group")}</button>
				</div>
			`);
			return;
		}
		const view = this.localSlice(group);
		const focus = document.activeElement && document.activeElement.classList.contains("fh-local-search");
		const cursor = focus ? document.activeElement.selectionStart : null;
		const title = group.group_name || group.name;
		this.detailEl.html(`
			<div class="fh-detail-head">
				<div style="flex:1">
					<label class="fh-name">
						<span class="fh-muted">${__("Group name")}</span>
						<input type="text" class="fh-group-name" value="${frappehero.esc(title)}" maxlength="140" autocomplete="off" aria-label="${__("Group name")}">
					</label>
					<div class="fh-colors">${this.colors
						.map(
							(color) =>
								`<button type="button" data-action="set-color" data-color="${color}" class="${
									frappehero.safe_color(group.color) === color ? "fh-on" : ""
								}" style="background:${color}" title="${color}"></button>`
						)
						.join("")}</div>
					<textarea class="fh-description">${frappehero.esc(group.description || "")}</textarea>
				</div>
				<div class="fh-actions">
					<label class="fh-check"><input type="checkbox" class="fh-enabled" ${group.enabled ? "checked" : ""}> ${__("Enabled")}</label>
					<button type="button" class="fh-btn" data-action="save-meta">${__("Save")}</button>
					<button type="button" class="fh-btn-danger" data-action="delete-group">${__("Delete")}</button>
				</div>
			</div>
			<p class="fh-muted">${frappehero.esc(group.sync_summary || __("Not synced yet."))}</p>
			<div class="fh-split">
				<div class="fh-section">
					<div class="fh-section-head">
						<strong>${__("Members")}</strong>
						<button type="button" class="fh-btn" data-action="add-members">${__("Add users")}</button>
					</div>
					<div class="fh-chips">${
						view.members
							.map(
								(member) => `
								<span class="fh-chip" title="${frappehero.esc((member.roles || []).join(", "))}">
									<span class="fh-avatar">${frappehero.esc(frappehero.initials(member.full_name))}</span>
									${frappehero.esc(member.full_name || member.user)}
									${!member.enabled ? `<span class="fh-muted">${__("disabled")}</span>` : ""}
									<button type="button" data-action="remove-member" data-user="${frappehero.esc(member.user)}" aria-label="${__("Remove")}">×</button>
								</span>`
							)
							.join("") || `<span class="fh-muted">${__("No members yet.")}</span>`
					}</div>
				</div>
				<div class="fh-section">
					<div class="fh-section-head">
						<strong>${__("Permitted values")}</strong>
						<button type="button" class="fh-btn" data-action="add-rules">${__("Add values")}</button>
					</div>
					<div>${
						view.rules
							.map((rule) => {
								const scope = rule.apply_to_all_doctypes
									? __("all document types")
									: __("only {0}", [rule.applicable_for || ""]);
								return `
									<div class="fh-rule">
										<div>
											<strong>${frappehero.esc(rule.reference_doctype)}</strong>
											${frappehero.esc(rule.for_value)}
											${rule.is_default ? `<span class="fh-pill fh-pill-sync">${__("Default")}</span>` : ""}
											<div class="fh-muted">${frappehero.esc(scope)}${rule.hide_descendants ? " · " + __("descendants hidden") : ""}</div>
										</div>
										<button type="button" class="fh-btn-quiet" data-action="remove-rule" data-rule="${frappehero.esc(rule.name)}">${__("Remove")}</button>
									</div>`;
							})
							.join("") || `<span class="fh-muted">${__("No permitted values yet.")}</span>`
					}</div>
				</div>
			</div>
			<div class="fh-section-head">
				<strong>${__("Who can use what")}</strong>
				<input type="search" class="fh-local-search" placeholder="${__("Filter this group")}" value="${frappehero.esc(this.localQuery)}">
			</div>
			${this.matrixHtml(view.members, view.rules)}
		`);
		if (focus) {
			const input = this.detailEl.find(".fh-local-search").get(0);
			input.focus();
			if (cursor != null) {
				input.setSelectionRange(cursor, cursor);
			}
		}
	}

	matrixHtml(members, rules) {
		const doctypes = [];
		rules.forEach((rule) => {
			if (rule.reference_doctype && !doctypes.includes(rule.reference_doctype)) {
				doctypes.push(rule.reference_doctype);
			}
		});
		if (!members.length || !doctypes.length) {
			return `<div class="fh-empty">${__("Add members and values to see the grid.")}</div>`;
		}
		const head = doctypes.map((doctype) => `<th>${frappehero.esc(doctype)}</th>`).join("");
		const body = members
			.map((member) => {
				const cells = doctypes
					.map((doctype) => {
						const values = rules.filter((rule) => rule.reference_doctype === doctype);
						return `<td>${values
							.map(
								(rule) =>
									`<div>${frappehero.esc(rule.for_value)}${rule.is_default ? " ★" : ""}</div>`
							)
							.join("")}</td>`;
					})
					.join("");
				return `<tr><td>${frappehero.esc(member.full_name || member.user)}</td>${cells}</tr>`;
			})
			.join("");
		return `<div class="fh-matrix-wrap"><table class="fh-matrix"><thead><tr><th>${__("User")}</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
	}

	onInput(event) {
		if (event.target.matches(".fh-search")) {
			clearTimeout(this.searchTimer);
			this.searchTimer = setTimeout(() => {
				this.filters.search = event.target.value || "";
				this.refresh();
			}, 250);
		}
		if (event.target.matches(".fh-local-search")) {
			this.localQuery = event.target.value || "";
			this.renderDetail();
		}
	}

	onKeydown(event) {
		if (event.key === "Enter" && event.target.matches(".fh-group-name")) {
			event.preventDefault();
			this.saveMeta();
		}
	}

	onChange(event) {
		if (event.target.matches(".fh-role")) {
			this.filters.role = event.target.value;
			this.refresh();
		} else if (event.target.matches(".fh-doctype")) {
			this.filters.doctype = event.target.value;
			this.refresh();
		} else if (event.target.matches(".fh-enabled")) {
			this.filters.enabled = event.target.value;
			this.refresh();
		} else if (event.target.matches(".fh-conflicts")) {
			this.filters.conflicts_only = event.target.checked ? 1 : 0;
			this.refresh();
		} else if (event.target.matches(".fh-enabled-toggle, .fh-enabled")) {
			this.saveMeta({ enabled: event.target.checked ? 1 : 0 });
		}
	}

	onClick(event) {
		const target = event.target.closest("[data-action]");
		if (!target) {
			return;
		}
		const action = target.dataset.action;
		if (action === "select-group") {
			this.selected = target.dataset.name;
			this.localQuery = "";
			this.renderList();
			this.renderDetail();
		} else if (action === "new-group") {
			this.openGroupDialog();
		} else if (action === "save-meta") {
			this.saveMeta();
		} else if (action === "set-color") {
			this.saveMeta({ color: target.dataset.color });
		} else if (action === "delete-group") {
			this.deleteSelected();
		} else if (action === "add-members") {
			this.openMemberDialog();
		} else if (action === "add-ungrouped") {
			this.addUsers([target.dataset.user]);
		} else if (action === "remove-member") {
			this.removeMember(target.dataset.user);
		} else if (action === "add-rules") {
			this.openRuleDialog();
		} else if (action === "remove-rule") {
			this.removeRule(target.dataset.rule);
		}
	}

	async saveMeta(overrides) {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		overrides = overrides || {};
		const description = this.detailEl.find(".fh-description").val();
		const nameInput = this.detailEl.find(".fh-group-name");
		const typedName = nameInput.length ? nameInput.val() : null;
		const enabled = Object.prototype.hasOwnProperty.call(overrides, "enabled")
			? overrides.enabled
			: this.detailEl.find(".fh-enabled").is(":checked")
				? 1
				: 0;
		const result = await frappehero.call("logistics.permission_studio.api.update_group", {
			name: group.name,
			group_name: typedName,
			description: description == null ? group.description : description,
			color: overrides.color || group.color,
			enabled,
		});
		const next = (result && result.name) || group.name;
		if (next !== group.name) {
			frappe.show_alert({ message: __("Renamed to {0}", [next]), indicator: "green" });
		}
		this.selected = next;
		await this.refresh();
		const routeName = frappe.get_route()[1];
		if (next !== group.name && routeName && decodeURIComponent(routeName) === group.name) {
			this.focusGroup = next;
			frappe.set_route("permission-studio", next);
		}
	}

	deleteSelected() {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		frappe.confirm(
			__("Delete {0}? User Permissions that only this group grants will be removed. Permissions also granted by another group stay.", [
				group.name,
			]),
			async () => {
				await frappehero.call("logistics.permission_studio.api.delete_group", { name: group.name });
				this.selected = null;
				this.refresh();
			}
		);
	}

	async syncAll() {
		await frappehero.call("logistics.permission_studio.api.sync_all");
		frappe.show_alert({ message: __("Permission groups synced"), indicator: "green" });
		this.refresh();
	}

	openGroupDialog() {
		const dialog = new frappe.ui.Dialog({
			title: __("New permission group"),
			fields: [
				{ fieldtype: "Data", fieldname: "group_name", label: __("Group Name"), reqd: 1 },
				{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
				{ fieldtype: "HTML", fieldname: "colors" },
				{ fieldtype: "Check", fieldname: "enabled", label: __("Enabled"), default: 1 },
			],
			primary_action_label: __("Create"),
			primary_action: async (values) => {
				const created = await frappehero.call("logistics.permission_studio.api.create_group", {
					group_name: values.group_name,
					description: values.description,
					color: dialog.hero_color || "#2490ef",
					enabled: values.enabled ? 1 : 0,
				});
				dialog.hide();
				this.focusGroup = created.name;
				this.refresh();
			},
		});
		dialog.hero_color = "#2490ef";
		dialog.fields_dict.colors.$wrapper.html(
			`<div class="fh-colors">${this.colors
				.map(
					(color) =>
						`<button type="button" data-color="${color}" class="${color === "#2490ef" ? "fh-on" : ""}" style="background:${color}"></button>`
				)
				.join("")}</div>`
		);
		dialog.fields_dict.colors.$wrapper.on("click", "button", (event) => {
			dialog.hero_color = event.currentTarget.dataset.color;
			dialog.fields_dict.colors.$wrapper.find("button").removeClass("fh-on");
			event.currentTarget.classList.add("fh-on");
		});
		dialog.show();
	}

	openMemberDialog() {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Add users to {0}", [group.name]),
			fields: [
				{ fieldtype: "Data", fieldname: "txt", label: __("Search") },
				{ fieldtype: "Link", fieldname: "role", label: __("Role"), options: "Role" },
				{
					fieldtype: "Select",
					fieldname: "user_type",
					label: __("User Type"),
					options: "\nSystem User\nWebsite User",
				},
				{ fieldtype: "Check", fieldname: "enabled_only", label: __("Enabled only"), default: 1 },
				{ fieldtype: "HTML", fieldname: "results" },
			],
			primary_action_label: __("Add selected"),
			primary_action: async () => {
				const users = [];
				dialog.fields_dict.results.$wrapper.find("input:checked").each(function () {
					users.push($(this).val());
				});
				if (!users.length) {
					frappe.msgprint(__("Select at least one user."));
					return;
				}
				await this.addUsers(users);
				dialog.hide();
			},
		});
		const reload = frappe.utils.debounce(() => this.loadUserChoices(dialog), 250);
		dialog.fields_dict.txt.$input.on("input", reload);
		dialog.fields_dict.role.df.onchange = reload;
		dialog.fields_dict.user_type.df.onchange = reload;
		dialog.fields_dict.enabled_only.df.onchange = reload;
		dialog.show();
		this.loadUserChoices(dialog);
	}

	async loadUserChoices(dialog) {
		const rows = await frappehero.call("logistics.permission_studio.api.search_users", {
			txt: dialog.get_value("txt"),
			role: dialog.get_value("role"),
			user_type: dialog.get_value("user_type"),
			enabled_only: dialog.get_value("enabled_only") ? 1 : 0,
		});
		const present = new Set((this.selectedGroup()?.members || []).map((member) => member.user));
		dialog.fields_dict.results.$wrapper.html(
			(rows || [])
				.map((user) => {
					const groups = (user.groups || []).join(", ");
					return `
						<label class="fh-pick">
							<input type="checkbox" value="${frappehero.esc(user.name)}" ${present.has(user.name) ? "disabled" : ""}>
							<span>
								<strong>${frappehero.esc(user.full_name || user.name)}</strong>
								<div class="fh-muted">${frappehero.esc(user.name)} · ${frappehero.esc((user.roles || []).slice(0, 4).join(", "))}${
									groups ? " · " + __("In {0}", [groups]) : ""
								}</div>
							</span>
						</label>`;
				})
				.join("") || `<div class="fh-muted">${__("No users match.")}</div>`
		);
	}

	async addUsers(users) {
		if (!this.selected) {
			frappe.msgprint(__("Choose a group first."));
			return;
		}
		await frappehero.call("logistics.permission_studio.api.add_members", {
			group: this.selected,
			users,
		});
		this.refresh();
	}

	async removeMember(user) {
		await frappehero.call("logistics.permission_studio.api.remove_member", {
			group: this.selected,
			user,
		});
		this.refresh();
	}

	openRuleDialog() {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Add permitted values"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "reference_doctype",
					label: __("DocType"),
					options: "DocType",
					reqd: 1,
					get_query: () => ({ query: "logistics.permission_studio.api.permitted_doctype_query" }),
				},
				{ fieldtype: "Data", fieldname: "value_search", label: __("Find values") },
				{ fieldtype: "HTML", fieldname: "values" },
				{
					fieldtype: "Check",
					fieldname: "apply_to_all_doctypes",
					label: __("Apply to all document types"),
					default: 1,
					description: __("Uncheck this to limit the permission to one document type, such as Sales Invoice."),
				},
				{
					fieldtype: "Link",
					fieldname: "applicable_for",
					label: __("Applicable For"),
					options: "DocType",
					depends_on: "eval:!doc.apply_to_all_doctypes",
					mandatory_depends_on: "eval:!doc.apply_to_all_doctypes",
					get_query: () => ({
						query: "frappe.core.doctype.user_permission.user_permission.get_applicable_for_doctype_list",
						doctype: dialog.get_value("reference_doctype"),
					}),
				},
				{ fieldtype: "Check", fieldname: "is_default", label: __("Use as default") },
				{
					fieldtype: "Check",
					fieldname: "hide_descendants",
					label: __("Hide descendants"),
					description: __("For tree documents, do not also grant child records."),
				},
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				const selected = [];
				dialog.fields_dict.values.$wrapper.find("input:checked").each(function () {
					selected.push($(this).val());
				});
				if (!values.reference_doctype || !selected.length) {
					frappe.msgprint(__("Choose a DocType and at least one value."));
					return;
				}
				await frappehero.call("logistics.permission_studio.api.add_rules", {
					group: group.name,
					rules: selected.map((value) => ({
						reference_doctype: values.reference_doctype,
						for_value: value,
						apply_to_all_doctypes: values.apply_to_all_doctypes ? 1 : 0,
						applicable_for: values.applicable_for,
						is_default: values.is_default ? 1 : 0,
						hide_descendants: values.hide_descendants ? 1 : 0,
					})),
				});
				dialog.hide();
				this.refresh();
			},
		});
		const reload = frappe.utils.debounce(() => this.loadValueChoices(dialog), 250);
		dialog.fields_dict.reference_doctype.df.onchange = () => {
			const nested = ((frappe.boot && frappe.boot.nested_set_doctypes) || []).includes(
				dialog.get_value("reference_doctype")
			);
			dialog.set_df_property("hide_descendants", "hidden", nested ? 0 : 1);
			this.loadValueChoices(dialog);
		};
		dialog.show();
		dialog.fields_dict.value_search.$input.on("input", reload);
		dialog.set_df_property("hide_descendants", "hidden", 1);
	}

	async loadValueChoices(dialog) {
		const doctype = dialog.get_value("reference_doctype");
		if (!doctype) {
			dialog.fields_dict.values.$wrapper.html(`<div class="fh-muted">${__("Choose a DocType.")}</div>`);
			return;
		}
		const rows = await frappehero.call("logistics.permission_studio.api.search_documents", {
			doctype,
			txt: dialog.get_value("value_search"),
		});
		dialog.fields_dict.values.$wrapper.html(
			(rows || [])
				.map(
					(row) => `
					<label class="fh-pick">
						<input type="checkbox" value="${frappehero.esc(row.name)}">
						<span><strong>${frappehero.esc(row.label || row.name)}</strong>
						${row.label && row.label !== row.name ? `<div class="fh-muted">${frappehero.esc(row.name)}</div>` : ""}</span>
					</label>`
				)
				.join("") || `<div class="fh-muted">${__("No values match. Try a different search.")}</div>`
		);
	}

	async removeRule(ruleName) {
		await frappehero.call("logistics.permission_studio.api.remove_rule", {
			group: this.selected,
			rule_name: ruleName,
		});
		this.refresh();
	}
};
