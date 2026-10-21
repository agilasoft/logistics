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
		this.selected = null;
		this.focusGroup = null;
		this.state = null;
		this.detailTab = "overview";
		this.checkedMembers = new Set();
		this.colors = ["#2490ef", "#5e64ff", "#db2777", "#d97706", "#16a34a", "#0891b2", "#7c3aed", "#dc2626"];
		this.page.main.addClass("ps-studio");
		this.page.set_title(__("Permission Studio"));
		if (this.page.set_title_sub) {
			this.page.set_title_sub(__("Manage user groups and permissions in one place"));
		}
		this.page.set_primary_action(__("New Group"), () => this.openGroupDialog(), "add");
		if (this.page.add_inner_button) {
			this.page.add_inner_button(__("Sync All"), () => this.syncAll());
		}
		this.page.main.html(`
			<div class="ps-desk">
				<div class="ps-cards"></div>
				<div class="ps-filterbar">
					<div class="ps-coverage">
						<div class="ps-coverage-track"><div class="ps-coverage-fill"></div></div>
						<span class="ps-coverage-label"></span>
					</div>
					<div class="ps-filters">
						<select class="ps-role" aria-label="${__("Role")}"></select>
						<select class="ps-doctype" aria-label="${__("DocType")}"></select>
						<select class="ps-enabled" aria-label="${__("Groups")}">
							<option value="all">${__("All groups")}</option>
							<option value="enabled">${__("Enabled")}</option>
							<option value="disabled">${__("Disabled")}</option>
						</select>
						<label class="ps-check"><input type="checkbox" class="ps-conflicts"> ${__("Conflicts only")}</label>
						<button type="button" class="ps-icon-btn" data-action="refresh" aria-label="${__("Refresh")}">${this.icon("refresh")}</button>
					</div>
				</div>
				<div class="ps-banner" hidden></div>
				<div class="ps-work">
					<aside class="ps-groups"></aside>
					<section class="ps-detail"></section>
				</div>
			</div>
		`);
		this.cardsEl = this.page.main.find(".ps-cards");
		this.bannerEl = this.page.main.find(".ps-banner");
		this.groupsEl = this.page.main.find(".ps-groups");
		this.detailEl = this.page.main.find(".ps-detail");
		const root = this.page.main.find(".ps-desk").get(0);
		root.addEventListener("click", (event) => this.onClick(event));
		root.addEventListener("change", (event) => this.onChange(event));
		root.addEventListener("input", (event) => this.onInput(event));
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
				this.checkedMembers = new Set();
			}
			this.render();
		} finally {
			this.page.main.removeClass("fh-loading");
		}
	}

	render() {
		const stats = this.state.stats || {};
		const grouped = Number(stats.grouped_users) || 0;
		const ungrouped = Number(stats.ungrouped_users) || 0;
		const enabledUsers = grouped + ungrouped;
		const percent = enabledUsers ? Math.round((grouped / enabledUsers) * 100) : 0;
		this.cardsEl.html(`
			${this.statCard("groups", stats.groups || 0, __("Groups"))}
			${this.statCard("users", grouped, __("Users in a group"), "is-green")}
			${this.statCard("user", ungrouped, __("Users with no group"), "is-purple")}
			${this.statCard("key", stats.grants || 0, __("User Permissions from groups"), "is-orange")}
		`);
		this.page.main.find(".ps-coverage-fill").css("width", `${percent}%`);
		this.page.main.find(".ps-coverage-label").text(
			__("{0}% of enabled users are in a permission group", [String(percent)])
		);
		const options = this.state.filter_options || {};
		this.fillFilter(".ps-role", options.roles || [], this.filters.role, __("All roles"));
		this.fillFilter(".ps-doctype", options.doctypes || [], this.filters.doctype, __("All DocTypes"));
		this.page.main.find(".ps-enabled").val(this.filters.enabled || "all");
		this.page.main.find(".ps-conflicts").prop("checked", !!this.filters.conflicts_only);
		const messages = this.state.messages || [];
		if (messages.length) {
			this.bannerEl.removeAttr("hidden").html(messages.map((message) => `<div>${frappehero.esc(message)}</div>`).join(""));
		} else {
			this.bannerEl.attr("hidden", "hidden").empty();
		}
		const search = this.page.main.find(".ps-group-search").get(0);
		const typing = search && document.activeElement === search;
		this.groupsEl.html(this.groupListHtml());
		this.detailEl.html(this.detailHtml());
		if (typing) {
			const input = this.page.main.find(".ps-group-search").get(0);
			if (input) {
				input.focus();
				const end = input.value.length;
				input.setSelectionRange(end, end);
			}
		}
	}

	fillFilter(selector, values, current, placeholder) {
		const select = this.page.main.find(selector);
		const signature = `${placeholder}|${values.join("|")}|${current || ""}`;
		if (select.attr("data-signature") === signature) {
			return;
		}
		select.html(
			`<option value="">${frappehero.esc(placeholder)}</option>` +
				values
					.map(
						(value) =>
							`<option value="${frappehero.esc(value)}" ${value === current ? "selected" : ""}>${frappehero.esc(value)}</option>`
					)
					.join("")
		);
		select.attr("data-signature", signature);
		select.val(current || "");
	}

	groupListHtml() {
		const groups = this.state.groups || [];
		const rows = groups
			.map((group) => {
				const title = group.group_name || group.name;
				return `<button type="button" class="ps-group ${group.name === this.selected ? "is-selected" : ""}" data-action="select-group" data-name="${frappehero.esc(group.name)}">
					<span class="ps-badge" style="background:${frappehero.safe_color(group.color)}">${frappehero.esc(frappehero.initials(title))}</span>
					<span class="ps-group-copy">
						<span><strong>${frappehero.esc(title)}</strong> <span class="ps-muted">${frappehero.esc(group.description || "")}</span></span>
						<span class="ps-muted">${__("{0} members · {1} rules", [String(group.members.length), String(group.rules.length)])}</span>
					</span>
					<span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span>
				</button>`;
			})
			.join("");
		return `<div class="ps-panel">
			<div class="ps-panel-head">
				<h2>${__("Groups")} (${groups.length})</h2>
				<button type="button" class="ps-btn-outline" data-action="new-group">${__("New Group")}</button>
			</div>
			<input type="search" class="ps-group-search" value="${frappehero.esc(this.filters.search || "")}" placeholder="${__("Search groups, users, values...")}">
			<div class="ps-group-scroll">${rows || `<div class="ps-empty">${__("No groups match these filters.")}</div>`}</div>
		</div>`;
	}

	statusClass(group) {
		if (!group.enabled) {
			return "is-muted";
		}
		if (group.sync_status === "In Sync") {
			return "is-sync";
		}
		if (group.sync_status === "Needs Attention") {
			return "is-attention";
		}
		return "";
	}

	statusLabel(group) {
		return group.enabled ? group.sync_status || __("Pending") : __("Disabled");
	}

	icon(name) {
		const paths = {
			groups: '<path d="M8 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3zm8 1a2.5 2.5 0 1 0-2.5-2.5A2.5 2.5 0 0 0 16 12zM2.5 19c.4-2.5 2.7-4 5.5-4s5.1 1.5 5.5 4z"/>',
			users: '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z"/>',
			user: '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z"/>',
			key: '<path d="M7.5 14a4.5 4.5 0 1 1 4.1-6H21v3h-2v2h-2v2h-3.2A4.5 4.5 0 0 1 7.5 14z"/>',
			refresh: '<path d="M17.6 6.4A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.2L13 11h7V4z"/>',
			info: '<path d="M7 3h8l5 5v12a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm7 1.5V9h4.5zM11 12h2v6h-2z"/>',
			trash: '<path d="M9 3h6l1 2h5v2H3V5h5zm1 6h2v8h-2zm4 0h2v8h-2zM6 9h2v8H6z"/>',
			pencil: '<path d="M3 17.2V21h3.8l11-11-3.8-3.8zM20.7 7.1a1 1 0 0 0 0-1.4l-2.4-2.4a1 1 0 0 0-1.4 0l-1.8 1.8 3.8 3.8z"/>',
		};
		return `<svg class="ps-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor">${paths[name] || ""}</svg>`;
	}

	statCard(iconName, value, label, tone) {
		return `<div class="ps-card"><span class="ps-card-icon ${tone || ""}">${this.icon(iconName)}</span><div><b>${frappehero.esc(value)}</b><span class="ps-muted">${label}</span></div></div>`;
	}

	selectedGroup() {
		return (this.state.groups || []).find((group) => group.name === this.selected) || null;
	}

	detailHtml() {
		const group = this.selectedGroup();
		if (!group) {
			return `<div class="ps-panel"><div class="ps-empty"><p>${__("Create a group, add the people in it, then add the companies, territories, or other values they may use.")}</p><button type="button" class="ps-btn" data-action="new-group">${__("New Group")}</button></div></div>`;
		}
		const title = group.group_name || group.name;
		const tabs = [
			["overview", __("Overview")],
			["members", __("Members ({0})", [String(group.members.length)])],
			["permissions", __("Permitted values ({0})", [String(group.rules.length)])],
			["matrix", __("Who can use what")],
			["activity", __("Activity")],
		];
		const tabButtons = tabs
			.map(
				([id, label]) =>
					`<button type="button" data-action="detail-tab" data-tab="${id}" class="${this.detailTab === id ? "is-on" : ""}">${label}</button>`
			)
			.join("");
		return `<div class="ps-panel">
			<div class="ps-detail-head">
				<span class="ps-badge lg" style="background:${frappehero.safe_color(group.color)}">${frappehero.esc(frappehero.initials(title))}</span>
				<div class="ps-detail-title">
					<div class="ps-title-row">
						<h2>${frappehero.esc(title)}</h2>
						<span class="ps-muted">${frappehero.esc(group.description || "")}</span>
						<span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span>
					</div>
					<p class="ps-muted">${frappehero.esc(group.sync_summary || __("Not synced yet."))}</p>
				</div>
				<button type="button" class="ps-btn-outline" data-action="edit-group">${this.icon("pencil")} ${__("Edit Group")}</button>
				<button type="button" class="ps-icon-btn ps-danger" data-action="delete-group" aria-label="${__("Delete")}">${this.icon("trash")}</button>
			</div>
			<div class="ps-tabs">${tabButtons}</div>
			${this.detailBody(group)}
		</div>`;
	}

	detailBody(group) {
		if (this.detailTab === "members") {
			return this.memberSection(group, true);
		}
		if (this.detailTab === "permissions") {
			return this.valueSection(group, true);
		}
		if (this.detailTab === "matrix") {
			return `<h3>${__("Who can use what")}</h3>${this.matrixHtml(group)}`;
		}
		if (this.detailTab === "activity") {
			const when = group.last_synced ? frappe.datetime.str_to_user(group.last_synced) : __("Not synced yet.");
			return `<p class="ps-muted">${__("Last synced")}</p><p>${frappehero.esc(when)}</p><p>${frappehero.esc(group.sync_summary || __("Not synced yet."))}</p>`;
		}
		return `${this.groupInfoHtml(group)}<div class="ps-split">${this.memberSection(group, false)}${this.valueSection(group, false)}</div>`;
	}

	groupInfoHtml(group) {
		const created = group.creation ? frappe.datetime.str_to_user(group.creation) : "—";
		const modified = group.modified ? frappe.datetime.str_to_user(group.modified) : "—";
		const swatches = this.colors
			.map(
				(color) =>
					`<button type="button" class="ps-swatch ${frappehero.safe_color(group.color) === color ? "is-on" : ""}" data-action="set-color" data-color="${color}" style="background:${color}" aria-label="${color}"></button>`
			)
			.join("");
		return `<div class="ps-info-card">
			<div class="ps-row-between"><strong>${this.icon("info")} ${__("Group Information")}</strong></div>
			<div class="ps-info-grid">
				<div>
					<div class="ps-field"><div class="ps-muted">${__("Group Name")}</div><div>${frappehero.esc(group.group_name || group.name)}</div></div>
					<div class="ps-field"><div class="ps-muted">${__("Description")}</div><div>${frappehero.esc(group.description || "—")}</div></div>
					<div class="ps-field"><div class="ps-muted">${__("Color")}</div><div class="ps-swatches">${swatches}</div></div>
				</div>
				<div>
					<div class="ps-field"><div class="ps-muted">${__("Status")}</div><div><span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span></div></div>
					<div class="ps-field"><div class="ps-muted">${__("Created On")}</div><div>${frappehero.esc(created)}</div></div>
					<div class="ps-field"><div class="ps-muted">${__("Last Modified")}</div><div>${frappehero.esc(modified)}</div></div>
					<div class="ps-field"><div class="ps-muted">${__("Total Members")}</div><div>${group.members.length}</div></div>
					<div class="ps-field"><div class="ps-muted">${__("Total Permissions")}</div><div>${group.rules.length}</div></div>
				</div>
			</div>
		</div>`;
	}

	memberSection(group, wide) {
		const removeChecked = this.checkedMembers.size
			? `<button type="button" class="ps-link ps-danger" data-action="remove-checked">${__("Remove selected")}</button>`
			: "";
		return `<div class="ps-box ${wide ? "is-wide" : ""}">
			<div class="ps-row-between"><strong>${__("Members")} (${group.members.length})</strong><span>${removeChecked}<button type="button" class="ps-btn-outline" data-action="add-members">${__("Add users")}</button></span></div>
			${this.memberTableHtml(group.members)}
		</div>`;
	}

	valueSection(group, wide) {
		return `<div class="ps-box ${wide ? "is-wide" : ""}">
			<div class="ps-row-between"><strong>${__("Permitted values")} (${group.rules.length})</strong><button type="button" class="ps-btn-outline" data-action="add-rules">${__("Add values")}</button></div>
			${this.valueTableHtml(group)}
		</div>`;
	}

	memberTableHtml(members) {
		const rows = (members || [])
			.map((member) => {
				const checked = this.checkedMembers.has(member.user) ? "checked" : "";
				return `<tr>
					<td><input type="checkbox" class="ps-member-check" data-user="${frappehero.esc(member.user)}" ${checked} aria-label="${__("Select")}"></td>
					<td><span class="ps-avatar">${frappehero.esc(frappehero.initials(member.full_name || member.user))}</span></td>
					<td>${frappehero.esc(member.full_name || member.user)}${member.enabled ? "" : ` <span class="ps-muted">${__("disabled")}</span>`}</td>
					<td class="ps-muted">${frappehero.esc(member.user)}</td>
					<td><button type="button" class="ps-icon-btn ps-danger" data-action="remove-member" data-user="${frappehero.esc(member.user)}" aria-label="${__("Remove")}">${this.icon("trash")}</button></td>
				</tr>`;
			})
			.join("");
		return `<div class="ps-table-scroll"><table class="ps-grid">
			<thead><tr><th></th><th></th><th>${__("Full name")}</th><th>${__("Username")}</th><th>${__("Actions")}</th></tr></thead>
			<tbody>${rows || `<tr><td colspan="5" class="ps-empty">${__("No members yet.")}</td></tr>`}</tbody>
		</table></div>`;
	}

	valueTableHtml(group) {
		const rows = (group.rules || [])
			.map((rule) => {
				const applicable = rule.apply_to_all_doctypes ? __("All Document Types") : rule.applicable_for || "";
				const title = rule.apply_to_all_doctypes ? __("all document types") : __("only {0}", [rule.applicable_for || ""]);
				return `<tr>
					<td>${frappehero.esc(rule.reference_doctype)}</td>
					<td>${frappehero.esc(rule.for_value)}${rule.is_default ? ` <span class="ps-pill is-sync">${__("Default")}</span>` : ""}</td>
					<td title="${frappehero.esc(title)}">${frappehero.esc(applicable)}</td>
					<td class="ps-actions">
						<button type="button" class="ps-btn-outline" data-action="edit-rule" data-group="${frappehero.esc(group.name)}" data-rule="${frappehero.esc(rule.name)}">${__("Edit")}</button>
						<button type="button" class="ps-icon-btn ps-danger" data-action="remove-rule" data-group="${frappehero.esc(group.name)}" data-rule="${frappehero.esc(rule.name)}" aria-label="${__("Remove")}">${this.icon("trash")}</button>
					</td>
				</tr>`;
			})
			.join("");
		return `<div class="ps-table-scroll"><table class="ps-grid">
			<thead><tr><th>${__("Field")}</th><th>${__("Value")}</th><th>${__("Applicable DocTypes")}</th><th>${__("Actions")}</th></tr></thead>
			<tbody>${rows || `<tr><td colspan="4" class="ps-empty">${__("No permitted values yet.")}</td></tr>`}</tbody>
		</table></div>`;
	}

	matrixHtml(group) {
		if (!group) {
			return `<div class="ps-empty">${__("Select a group to see who can use what.")}</div>`;
		}
		const matrix = group.matrix || { doctypes: [], rows: [] };
		if (!matrix.rows.length || !matrix.doctypes.length) {
			return `<div class="ps-empty">${__("Add members and permitted values to see who can use what.")}</div>`;
		}
		const head = matrix.doctypes.map((doctype) => `<th>${frappehero.esc(doctype)}</th>`).join("");
		const body = matrix.rows
			.map((row) => {
				const cells = matrix.doctypes
					.map((doctype) => {
						const values = row.cells[doctype] || [];
						return `<td>${values.map((cell) => `<div>${frappehero.esc(cell.value)}${cell.is_default ? " ★" : ""}</div>`).join("")}</td>`;
					})
					.join("");
				return `<tr><td>${frappehero.esc(row.full_name || row.user)}</td>${cells}</tr>`;
			})
			.join("");
		return `<div class="ps-table-scroll"><table class="ps-grid"><thead><tr><th>${__("User")}</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
	}

	onInput(event) {
		if (!event.target.matches(".ps-group-search")) {
			return;
		}
		clearTimeout(this.searchTimer);
		const value = event.target.value || "";
		this.searchTimer = setTimeout(() => {
			this.filters.search = value;
			this.refresh();
		}, 250);
	}

	onChange(event) {
		const target = event.target;
		if (target.matches(".ps-role")) {
			this.filters.role = target.value || "";
			this.refresh();
		} else if (target.matches(".ps-doctype")) {
			this.filters.doctype = target.value || "";
			this.refresh();
		} else if (target.matches(".ps-enabled")) {
			this.filters.enabled = target.value || "all";
			this.refresh();
		} else if (target.matches(".ps-conflicts")) {
			this.filters.conflicts_only = target.checked ? 1 : 0;
			this.refresh();
		} else if (target.matches(".ps-member-check")) {
			if (target.checked) {
				this.checkedMembers.add(target.dataset.user);
			} else {
				this.checkedMembers.delete(target.dataset.user);
			}
			this.render();
		}
	}

	onClick(event) {
		const target = event.target.closest("[data-action]");
		if (!target || target.disabled) {
			return;
		}
		const action = target.dataset.action;
		if (action === "select-group") {
			if (this.selected !== target.dataset.name) {
				this.checkedMembers = new Set();
			}
			this.selected = target.dataset.name;
			this.render();
		} else if (action === "detail-tab") {
			this.detailTab = target.dataset.tab || "overview";
			this.render();
		} else if (action === "refresh") {
			this.refresh();
		} else if (action === "new-group") {
			this.openGroupDialog();
		} else if (action === "edit-group") {
			this.openEditGroupDialog();
		} else if (action === "set-color") {
			this.saveMeta({ color: target.dataset.color });
		} else if (action === "delete-group") {
			this.deleteSelected();
		} else if (action === "add-members") {
			this.openMemberDialog();
		} else if (action === "remove-member") {
			this.checkedMembers.delete(target.dataset.user);
			this.removeMember(target.dataset.user);
		} else if (action === "remove-checked") {
			this.removeCheckedMembers();
		} else if (action === "add-rules") {
			this.openRuleDialog();
		} else if (action === "edit-rule") {
			this.openEditRule(target.dataset.rule, target.dataset.group);
		} else if (action === "remove-rule") {
			this.removeRule(target.dataset.rule, target.dataset.group);
		}
	}

	async removeCheckedMembers() {
		const users = [...this.checkedMembers];
		this.checkedMembers = new Set();
		for (const user of users) {
			await frappehero.call("logistics.permission_studio.api.remove_member", {
				group: this.selected,
				user,
			});
		}
		this.refresh();
	}


	async saveMeta(overrides) {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		overrides = overrides || {};
		const typedName = Object.prototype.hasOwnProperty.call(overrides, "group_name")
			? overrides.group_name
			: group.group_name || group.name;
		const description = Object.prototype.hasOwnProperty.call(overrides, "description")
			? overrides.description
			: group.description;
		const enabled = Object.prototype.hasOwnProperty.call(overrides, "enabled")
			? overrides.enabled
			: group.enabled
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

	bindColorPicker(dialog, current) {
		const selected = frappehero.safe_color(current || "#2490ef");
		dialog.hero_color = selected;
		dialog.fields_dict.colors.$wrapper.html(
			`<div class="fh-colors">${this.colors
				.map(
					(color) =>
						`<button type="button" data-color="${color}" class="${selected === color ? "fh-on" : ""}" style="background:${color}"></button>`
				)
				.join("")}</div>`
		);
		dialog.fields_dict.colors.$wrapper.on("click", "button", (event) => {
			dialog.hero_color = event.currentTarget.dataset.color;
			dialog.fields_dict.colors.$wrapper.find("button").removeClass("fh-on");
			event.currentTarget.classList.add("fh-on");
		});
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
		this.bindColorPicker(dialog, "#2490ef");
		dialog.show();
	}

	openEditGroupDialog() {
		const group = this.selectedGroup();
		if (!group) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Edit group"),
			fields: [
				{
					fieldtype: "Data",
					fieldname: "group_name",
					label: __("Group Name"),
					reqd: 1,
					default: group.group_name || group.name,
				},
				{
					fieldtype: "Small Text",
					fieldname: "description",
					label: __("Description"),
					default: group.description || "",
				},
				{ fieldtype: "HTML", fieldname: "colors" },
				{ fieldtype: "Check", fieldname: "enabled", label: __("Enabled"), default: group.enabled ? 1 : 0 },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await this.saveMeta({
					group_name: values.group_name,
					description: values.description,
					color: dialog.hero_color,
					enabled: values.enabled ? 1 : 0,
				});
				dialog.hide();
			},
		});
		this.bindColorPicker(dialog, group.color);
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
				dialog.fields_dict.values.$wrapper.find("input[data-key]:checked:not(:disabled)").each((_, input) => {
					this.rememberPick(dialog, input);
				});
				const selected = [...(dialog.hero_picks || new Map()).values()];
				if (!selected.length) {
					frappe.msgprint(__("Choose a DocType and at least one value."));
					return;
				}
				await frappehero.call("logistics.permission_studio.api.add_rules", {
					group: group.name,
					rules: selected.map((pick) => ({
						reference_doctype: pick.doctype,
						for_value: pick.name,
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
		dialog.hero_picks = new Map();
		dialog.fields_dict.values.$wrapper.on("change", "input[data-key]", (event) => {
			this.rememberPick(dialog, event.target);
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

	pickKey(doctype, name) {
		return `${encodeURIComponent(doctype)}:${encodeURIComponent(name)}`;
	}

	rememberPick(dialog, input) {
		if (!dialog.hero_picks) {
			dialog.hero_picks = new Map();
		}
		if (input.disabled) {
			return;
		}
		const key = input.dataset.key || this.pickKey(input.dataset.doctype, input.value);
		if (!key) {
			return;
		}
		if (input.checked) {
			dialog.hero_picks.set(key, {
				doctype: input.dataset.doctype,
				name: input.value,
				label: input.dataset.label || input.value,
			});
		} else {
			dialog.hero_picks.delete(key);
		}
	}

	async loadValueChoices(dialog) {
		if (!dialog.hero_picks) {
			dialog.hero_picks = new Map();
		}
		const doctype = dialog.get_value("reference_doctype");
		const token = (dialog.hero_search_token || 0) + 1;
		dialog.hero_search_token = token;
		if (!doctype) {
			dialog.fields_dict.values.$wrapper.html(`<div class="fh-muted">${__("Choose a DocType.")}</div>`);
			return;
		}
		const rows = await frappehero.call("logistics.permission_studio.api.search_documents", {
			doctype,
			txt: dialog.get_value("value_search"),
		});
		if (token !== dialog.hero_search_token) {
			return;
		}
		dialog.fields_dict.values.$wrapper.html(this.valueChoiceHtml(dialog, doctype, rows || []));
	}

	valueChoiceHtml(dialog, doctype, rows) {
		const picks = dialog.hero_picks || new Map();
		const group = this.selectedGroup();
		const seen = new Set();
		const blocks = [];
		const push = (row) => {
			if (!row || seen.has(row.key)) {
				return;
			}
			seen.add(row.key);
			blocks.push(this.valueChoiceRow(row));
		};
		(group?.rules || []).forEach((rule) => {
			if (!rule.reference_doctype || rule.reference_doctype === doctype) {
				return;
			}
			push({
				key: this.pickKey(rule.reference_doctype, rule.for_value),
				doctype: rule.reference_doctype,
				name: rule.for_value,
				label: rule.for_value,
				checked: true,
				disabled: true,
				other: true,
				note: __("Already on this group"),
			});
		});
		picks.forEach((pick) => {
			if (pick.doctype === doctype) {
				return;
			}
			push({
				key: this.pickKey(pick.doctype, pick.name),
				doctype: pick.doctype,
				name: pick.name,
				label: pick.label || pick.name,
				checked: true,
				disabled: false,
				other: true,
				note: __("Tagged on another DocType"),
			});
		});
		const resultNames = new Set((rows || []).map((row) => row.name));
		picks.forEach((pick) => {
			if (pick.doctype !== doctype || resultNames.has(pick.name)) {
				return;
			}
			push({
				key: this.pickKey(pick.doctype, pick.name),
				doctype: pick.doctype,
				name: pick.name,
				label: pick.label || pick.name,
				checked: true,
				disabled: false,
				other: false,
				note: "",
			});
		});
		(rows || []).forEach((row) => {
			const key = this.pickKey(doctype, row.name);
			const already = (group?.rules || []).some(
				(rule) => rule.reference_doctype === doctype && rule.for_value === row.name
			);
			push({
				key,
				doctype,
				name: row.name,
				label: row.label || row.name,
				checked: already || picks.has(key),
				disabled: already,
				other: false,
				note: already ? __("Already on this group") : "",
				sub: row.label && row.label !== row.name ? row.name : "",
			});
		});
		const body = blocks.join("") || `<div class="fh-muted">${__("No values match. Try a different search.")}</div>`;
		return `<div class="ps-value-scroll">${body}</div>`;
	}

	valueChoiceRow(row) {
		return `<label class="fh-pick ${row.other ? "is-other" : ""}">
			<input type="checkbox" data-key="${frappehero.esc(row.key)}" data-doctype="${frappehero.esc(row.doctype)}" data-label="${frappehero.esc(row.label || row.name)}" value="${frappehero.esc(row.name)}" ${row.checked ? "checked" : ""} ${row.disabled ? "disabled" : ""}>
			<span>
				<strong>${frappehero.esc(row.label || row.name)}</strong>
				${row.other ? `<span class="ps-pill">${frappehero.esc(row.doctype)}</span>` : ""}
				${row.note ? `<div class="fh-muted">${frappehero.esc(row.note)}</div>` : ""}
				${row.sub ? `<div class="fh-muted">${frappehero.esc(row.sub)}</div>` : ""}
			</span>
		</label>`;
	}

	openEditRule(ruleName, groupName) {
		const group = groupName
			? (this.state.groups || []).find((row) => row.name === groupName) || this.selectedGroup()
			: this.selectedGroup();
		if (!group) {
			return;
		}
		const rule = (group.rules || []).find((row) => row.name === ruleName);
		if (!rule) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Edit permitted value"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "reference_doctype",
					label: __("DocType"),
					options: "DocType",
					reqd: 1,
					default: rule.reference_doctype,
					get_query: () => ({ query: "logistics.permission_studio.api.permitted_doctype_query" }),
				},
				{
					fieldtype: "Dynamic Link",
					fieldname: "for_value",
					label: __("Value"),
					options: "reference_doctype",
					reqd: 1,
					default: rule.for_value,
				},
				{
					fieldtype: "Check",
					fieldname: "apply_to_all_doctypes",
					label: __("Apply to all document types"),
					default: rule.apply_to_all_doctypes ? 1 : 0,
					description: __("Uncheck this to limit the permission to one document type, such as Sales Invoice."),
				},
				{
					fieldtype: "Link",
					fieldname: "applicable_for",
					label: __("Applicable For"),
					options: "DocType",
					default: rule.applicable_for || "",
					depends_on: "eval:!doc.apply_to_all_doctypes",
					mandatory_depends_on: "eval:!doc.apply_to_all_doctypes",
					get_query: () => ({
						query: "frappe.core.doctype.user_permission.user_permission.get_applicable_for_doctype_list",
						doctype: dialog.get_value("reference_doctype"),
					}),
				},
				{ fieldtype: "Check", fieldname: "is_default", label: __("Use as default"), default: rule.is_default ? 1 : 0 },
				{
					fieldtype: "Check",
					fieldname: "hide_descendants",
					label: __("Hide descendants"),
					default: rule.hide_descendants ? 1 : 0,
					description: __("For tree documents, do not also grant child records."),
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				if (!values.reference_doctype || !values.for_value) {
					frappe.msgprint(__("Choose a DocType and a value."));
					return;
				}
				await frappehero.call("logistics.permission_studio.api.update_rule", {
					group: group.name,
					rule_name: rule.name,
					reference_doctype: values.reference_doctype,
					for_value: values.for_value,
					apply_to_all_doctypes: values.apply_to_all_doctypes ? 1 : 0,
					applicable_for: values.applicable_for,
					is_default: values.is_default ? 1 : 0,
					hide_descendants: values.hide_descendants ? 1 : 0,
				});
				dialog.hide();
				this.refresh();
			},
		});
		dialog.show();
		const nestedNow = () =>
			((frappe.boot && frappe.boot.nested_set_doctypes) || []).includes(dialog.get_value("reference_doctype"));
		dialog.set_df_property("hide_descendants", "hidden", nestedNow() ? 0 : 1);
		dialog.fields_dict.reference_doctype.df.onchange = () => {
			if (dialog.get_value("reference_doctype") !== rule.reference_doctype) {
				dialog.set_value("for_value", "");
			}
			dialog.set_df_property("hide_descendants", "hidden", nestedNow() ? 0 : 1);
		};
	}

	async removeRule(ruleName, groupName) {
		await frappehero.call("logistics.permission_studio.api.remove_rule", {
			group: groupName || this.selected,
			rule_name: ruleName,
		});
		this.refresh();
	}
};
