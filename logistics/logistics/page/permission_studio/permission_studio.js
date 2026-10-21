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
		this.section = "overview";
		this.detailTab = "overview";
		this.statusFilter = "all";
		this.pageStart = 0;
		this.pageSize = 10;
		this.colors = ["#2490ef", "#5e64ff", "#db2777", "#d97706", "#16a34a", "#0891b2", "#7c3aed", "#dc2626"];
		const fullName = (frappe.session && (frappe.session.user_fullname || frappe.session.user)) || "";
		const userId = (frappe.session && frappe.session.user) || "";
		this.page.main.addClass("ps-studio");
		if (this.page.wrapper) {
			$(this.page.wrapper).find(".page-head").addClass("ps-hide-head");
		}
		this.page.main.html(`
			<div class="ps-app">
				<div class="ps-top">
					<div class="ps-brand">
						<div class="ps-logo">P</div>
						<div>
							<h1>${__("Permission Studio")}</h1>
							<p>${__("Manage user groups and permissions in one place")}</p>
						</div>
					</div>
					<input type="search" class="ps-top-search" placeholder="${__("Search groups, users, values")}">
					<div class="ps-user">
						<span class="ps-avatar">${frappehero.esc(frappehero.initials(fullName))}</span>
						<span class="ps-user-text"><strong>${frappehero.esc(fullName)}</strong>${
							userId && userId !== fullName ? `<span class="ps-muted">${frappehero.esc(userId)}</span>` : ""
						}</span>
					</div>
				</div>
				<div class="ps-layout">
					<nav class="ps-nav">
						<button type="button" data-section="overview">${this.icon("home")}<span>${__("Overview")}</span></button>
						<button type="button" data-section="groups">${this.icon("groups")}<span>${__("Permission Groups")}</span></button>
						<button type="button" data-section="users">${this.icon("users")}<span>${__("Users")}</span></button>
						<button type="button" data-section="matrix">${this.icon("grid")}<span>${__("Permission Matrix")}</span></button>
						<button type="button" data-section="access">${this.icon("eye")}<span>${__("View User Access")}</span></button>
						<div class="ps-quick">
							<p>${__("Quick Actions")}</p>
							<button type="button" data-action="sync-all">${this.icon("refresh")}<span>${__("Sync All")}</span></button>
							<button type="button" data-action="new-group">${this.icon("plus")}<span>${__("Create Group")}</span></button>
							<button type="button" data-action="coverage">${this.icon("shield")}<span>${__("Permission Coverage")}</span></button>
						</div>
					</nav>
					<div class="ps-main">
						<div class="ps-banner" hidden></div>
						<div class="ps-cards"></div>
						<div class="ps-stage"></div>
					</div>
				</div>
			</div>
		`);
		this.bannerEl = this.page.main.find(".ps-banner");
		this.cardsEl = this.page.main.find(".ps-cards");
		this.stageEl = this.page.main.find(".ps-stage");
		const root = this.page.main.find(".ps-app").get(0);
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
			}
			this.render();
		} finally {
			this.page.main.removeClass("fh-loading");
		}
	}

	render() {
		const stats = this.state.stats || {};
		const issues = (this.state.messages || []).length;
		this.page.main.find(".ps-nav button[data-section]").each((_, button) => {
			button.classList.toggle("is-on", button.dataset.section === this.section);
		});
		this.cardsEl.html(`
			${this.statCard("groups", stats.groups || 0, __("Permission Groups"), "")}
			${this.statCard("users", stats.grouped_users || 0, __("Users in a group"), "is-green")}
			${this.statCard("user", stats.ungrouped_users || 0, __("Users without a group"), "is-purple")}
			${this.statCard("key", stats.grants || 0, __("User Permissions from groups"), "is-orange")}
			${this.statCard("alert", issues, __("Permission issues"), issues ? "is-alert" : "", issues ? __("Requires attention") : "")}
		`);
		const messages = this.state.messages || [];
		if (messages.length) {
			this.bannerEl.removeAttr("hidden").html(messages.map((message) => `<div>${frappehero.esc(message)}</div>`).join(""));
		} else {
			this.bannerEl.attr("hidden", "hidden").empty();
		}
		const topSearch = this.page.main.find(".ps-top-search").get(0);
		if (topSearch && document.activeElement !== topSearch) {
			topSearch.value = this.filters.search || "";
		}
		if (this.section === "users") {
			this.stageEl.html(this.usersHtml());
		} else if (this.section === "matrix") {
			this.stageEl.html(`<div class="ps-panel"><h2>${__("Permission Matrix")}</h2>${this.matrixHtml(this.selectedGroup())}</div>`);
		} else if (this.section === "access") {
			this.stageEl.html(this.accessHtml());
		} else {
			this.stageEl.html(`<div class="ps-work">${this.tableHtml()}${this.detailHtml()}</div>`);
		}
	}

	visibleGroups() {
		let groups = this.state.groups || [];
		if (this.statusFilter === "Disabled") {
			groups = groups.filter((group) => !group.enabled);
		} else if (this.statusFilter !== "all") {
			groups = groups.filter((group) => group.enabled && group.sync_status === this.statusFilter);
		}
		return groups;
	}

	tableHtml() {
		const groups = this.visibleGroups();
		if (this.pageStart >= groups.length) {
			this.pageStart = groups.length ? Math.floor((groups.length - 1) / this.pageSize) * this.pageSize : 0;
		}
		const start = this.pageStart;
		const page = groups.slice(start, start + this.pageSize);
		const rows = page
			.map((group) => {
				const title = group.group_name || group.name;
				const when = group.modified ? frappe.datetime.str_to_user(group.modified) : "";
				return `<tr class="${group.name === this.selected ? "is-selected" : ""}">
					<td><input type="checkbox" data-action="select-group" data-name="${frappehero.esc(group.name)}" ${group.name === this.selected ? "checked" : ""}></td>
					<td><button type="button" class="ps-name" data-action="select-group" data-name="${frappehero.esc(group.name)}">
						<span class="ps-badge" style="background:${frappehero.safe_color(group.color)}">${frappehero.esc(frappehero.initials(title))}</span>
						<span><strong>${frappehero.esc(title)}</strong><div class="ps-muted">${frappehero.esc(group.description || "")}</div></span>
					</button></td>
					<td>${group.members.length}</td>
					<td>${group.rules.length}</td>
					<td><span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span></td>
					<td><div>${frappehero.esc(when)}</div><div class="ps-muted">${frappehero.esc(group.modified_by || "")}</div></td>
				</tr>`;
			})
			.join("");
		const end = Math.min(start + this.pageSize, groups.length);
		return `<section class="ps-panel">
			<div class="ps-panel-head">
				<div><h2>${__("Permission Groups")}</h2><p class="ps-muted">${__("Manage and configure permission groups for your organization.")}</p></div>
				<button type="button" class="ps-btn" data-action="new-group">${__("New Group")}</button>
			</div>
			<div class="ps-toolbar">
				<input type="search" class="ps-table-search" value="${frappehero.esc(this.filters.search || "")}" placeholder="${__("Search groups...")}">
				<select class="ps-status">
					<option value="all" ${this.statusFilter === "all" ? "selected" : ""}>${__("All Statuses")}</option>
					<option value="In Sync" ${this.statusFilter === "In Sync" ? "selected" : ""}>${__("In Sync")}</option>
					<option value="Needs Attention" ${this.statusFilter === "Needs Attention" ? "selected" : ""}>${__("Needs Attention")}</option>
					<option value="Pending" ${this.statusFilter === "Pending" ? "selected" : ""}>${__("Pending")}</option>
					<option value="Disabled" ${this.statusFilter === "Disabled" ? "selected" : ""}>${__("Disabled")}</option>
				</select>
				<button type="button" class="ps-btn-quiet" data-action="refresh">${__("Refresh")}</button>
			</div>
			<table class="ps-table">
				<thead><tr>
					<th></th><th>${__("Group Name")}</th><th>${__("Members")}</th><th>${__("Permitted Values")}</th><th>${__("Status")}</th><th>${__("Last Modified")}</th>
				</tr></thead>
				<tbody>${rows || `<tr><td colspan="6" class="ps-empty">${__("No groups match these filters.")}</td></tr>`}</tbody>
			</table>
			<div class="ps-pager">
				<span>${groups.length ? __("Showing {0}–{1} of {2} groups", [String(start + 1), String(end), String(groups.length)]) : __("No groups")}</span>
				<span class="ps-pages">${this.pageButtons(groups.length, start)}</span>
			</div>
		</section>`;
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
			home: '<path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z"/>',
			groups: '<path d="M4 5h7v7H4zm9 0h7v7h-7zM4 14h7v7H4zm9 3h7v4h-7z"/>',
			users: '<path d="M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8 1a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM2.5 19c.4-2.4 2.6-4 5.5-4s5.1 1.6 5.5 4h.1c-.2-1.6-1.2-3-2.8-3.7 1.9.2 3.4 1.5 3.9 3.7z"/>',
			user: '<path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-3.3 0-8 1.7-8 5v1h16v-1c0-3.3-4.7-5-8-5z"/>',
			grid: '<path d="M4 4h7v7H4zm9 0h7v7h-7zM4 13h7v7H4zm9 0h7v7h-7z"/>',
			eye: '<path d="M12 6C7 6 3.1 9.1 2 12c1.1 2.9 5 6 10 6s8.9-3.1 10-6c-1.1-2.9-5-6-10-6zm0 10a4 4 0 1 1 4-4 4 4 0 0 1-4 4z"/>',
			refresh: '<path d="M17.6 6.4A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.2L13 11h7V4z"/>',
			plus: '<path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z"/>',
			shield: '<path d="M12 3 5 6v6c0 4.2 2.9 7.4 7 9 4.1-1.6 7-4.8 7-9V6z"/>',
			key: '<path d="M7.5 14a4.5 4.5 0 1 1 4.1-6H21v3h-2v2h-2v2h-3.2A4.5 4.5 0 0 1 7.5 14z"/>',
			alert: '<path d="M12 3 2 20h20zm-1 6h2v6h-2zm0 8h2v2h-2z"/>',
		};
		return `<svg class="ps-icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="currentColor">${paths[name] || ""}</svg>`;
	}

	statCard(iconName, value, label, tone, note) {
		return `<div class="ps-card ${tone || ""}"><span class="ps-card-icon ${tone || ""}">${this.icon(iconName)}</span><div><b>${frappehero.esc(value)}</b><span class="ps-muted">${label}</span>${note ? `<span class="ps-note">${note}</span>` : ""}</div></div>`;
	}

	pageButtons(total, start) {
		const pages = Math.max(Math.ceil(total / this.pageSize), 1);
		const current = Math.floor(start / this.pageSize) + 1;
		let from = 1;
		let to = pages;
		if (pages > 7) {
			from = Math.max(1, current - 2);
			to = Math.min(pages, from + 4);
			from = Math.max(1, to - 4);
		}
		const buttons = [
			`<button type="button" class="ps-page" data-action="page-go" data-page="${current - 1}" ${current === 1 ? "disabled" : ""} aria-label="${__("Previous")}">‹</button>`,
		];
		for (let page = from; page <= to; page++) {
			buttons.push(
				`<button type="button" class="ps-page ${page === current ? "is-on" : ""}" data-action="page-go" data-page="${page}">${page}</button>`
			);
		}
		buttons.push(
			`<button type="button" class="ps-page" data-action="page-go" data-page="${current + 1}" ${current === pages ? "disabled" : ""} aria-label="${__("Next")}">›</button>`
		);
		return buttons.join("");
	}

	selectedGroup() {
		return (this.state.groups || []).find((group) => group.name === this.selected) || null;
	}

	detailHtml() {
		const group = this.selectedGroup();
		if (!group) {
			return `<section class="ps-panel"><div class="ps-empty">
				<p>${__("Create a group, add the people in it, then add the companies, territories, or other values they may use.")}</p>
				<button type="button" class="ps-btn" data-action="new-group">${__("New Group")}</button>
			</div></section>`;
		}
		const title = group.group_name || group.name;
		const tabs = [
			["overview", __("Overview")],
			["members", __("Members")],
			["permissions", __("Permissions")],
			["activity", __("Activity")],
		];
		const tabButtons = tabs
			.map(
				([id, label]) =>
					`<button type="button" data-action="detail-tab" data-tab="${id}" class="${this.detailTab === id ? "is-on" : ""}">${label}</button>`
			)
			.join("");
		return `<section class="ps-panel">
			<div class="ps-detail-head">
				<span class="ps-badge" style="background:${frappehero.safe_color(group.color)}">${frappehero.esc(frappehero.initials(title))}</span>
				<div style="flex:1">
					<div class="ps-title-row">
						<h2>${frappehero.esc(title)}</h2>
						<span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span>
					</div>
					<p class="ps-muted">${frappehero.esc(group.description || __("No description"))}</p>
				</div>
				<div class="ps-detail-actions">
					<button type="button" class="ps-btn-outline" data-action="edit-group">${__("Edit Group")}</button>
					<button type="button" class="ps-link ps-danger" data-action="delete-group">${__("Delete")}</button>
				</div>
			</div>
			<div class="ps-tabs">${tabButtons}</div>
			${this.detailBody(group)}
		</section>`;
	}

	detailBody(group) {
		if (this.detailTab === "members") {
			return `<div class="ps-row-between"><strong>${__("Members")}</strong><button type="button" class="ps-btn-outline" data-action="add-members">${__("Add users")}</button></div>${this.memberRowsHtml(group.members)}`;
		}
		if (this.detailTab === "permissions") {
			return `<div class="ps-row-between"><strong>${__("Permitted values")}</strong><button type="button" class="ps-btn-outline" data-action="add-rules">${__("Add values")}</button></div>${this.valueRowsHtml(group.rules, group.name)}`;
		}
		if (this.detailTab === "activity") {
			const when = group.last_synced ? frappe.datetime.str_to_user(group.last_synced) : __("Not synced yet.");
			return `<p class="ps-muted">${__("Last synced")}</p><p>${frappehero.esc(when)}</p><p>${frappehero.esc(group.sync_summary || __("Not synced yet."))}</p>`;
		}
		const created = group.creation ? frappe.datetime.str_to_user(group.creation) : "";
		const modified = group.modified ? frappe.datetime.str_to_user(group.modified) : "";
		return `
			<div class="ps-row-between"><strong>${__("Group Information")}</strong></div>
			<div class="ps-info">
				<div><div class="ps-muted">${__("Group Name")}</div><strong>${frappehero.esc(group.group_name || group.name)}</strong></div>
				<div><div class="ps-muted">${__("Description")}</div><strong>${frappehero.esc(group.description || "—")}</strong></div>
				<div><div class="ps-muted">${__("Created On")}</div><strong>${frappehero.esc(created || "—")}</strong></div>
				<div><div class="ps-muted">${__("Last Modified")}</div><strong>${frappehero.esc(modified || "—")}</strong></div>
			</div>
			<div class="ps-split">
				<div class="ps-box">
					<div class="ps-row-between"><strong>${__("Members")}</strong><button type="button" class="ps-btn-outline" data-action="add-members">${__("Add users")}</button></div>
					${this.memberRowsHtml(group.members)}
				</div>
				<div class="ps-box">
					<div class="ps-row-between"><strong>${__("Permitted values")}</strong><button type="button" class="ps-btn-outline" data-action="add-rules">${__("Add values")}</button></div>
					${this.valueRowsHtml(group.rules, group.name)}
				</div>
			</div>
			<div class="ps-summary">
				<strong>${__("Group Access Summary")}</strong>
				${this.accessSummaryHtml(group)}
			</div>`;
	}

	memberRowsHtml(members) {
		return (
			(members || [])
				.map((member) => {
					const roles = (member.roles || []).slice(0, 3).join(", ");
					return `<div class="ps-person">
						<span class="ps-avatar">${frappehero.esc(frappehero.initials(member.full_name || member.user))}</span>
						<div>
							<strong>${frappehero.esc(member.full_name || member.user)}</strong>
							<div class="ps-muted">${roles ? frappehero.esc(roles) : frappehero.esc(member.user)}${member.enabled ? "" : " · " + __("disabled")}</div>
						</div>
						<button type="button" class="ps-link" data-action="remove-member" data-user="${frappehero.esc(member.user)}">${__("Remove")}</button>
					</div>`;
				})
				.join("") || `<div class="ps-muted">${__("No members yet.")}</div>`
		);
	}

	valueRowsHtml(rules, groupName) {
		const owner = groupName || this.selected || "";
		return (
			(rules || [])
				.map((rule) => {
					const scope = rule.apply_to_all_doctypes
						? __("all document types")
						: __("only {0}", [rule.applicable_for || ""]);
					const extra = rule.hide_descendants ? " · " + __("descendants hidden") : "";
					return `<div class="ps-value">
						<div>
							<strong>${frappehero.esc(rule.reference_doctype)}</strong>
							<div>${frappehero.esc(rule.for_value)}${rule.is_default ? ` <span class="ps-pill is-sync">${__("Default")}</span>` : ""}</div>
							<div class="ps-muted">${frappehero.esc(scope)}${frappehero.esc(extra)}</div>
						</div>
						<div class="ps-value-actions">
							<button type="button" class="ps-btn-outline" data-action="edit-rule" data-group="${frappehero.esc(owner)}" data-rule="${frappehero.esc(rule.name)}">${__("Edit")}</button>
							<button type="button" class="ps-link" data-action="remove-rule" data-group="${frappehero.esc(owner)}" data-rule="${frappehero.esc(rule.name)}">${__("Remove")}</button>
						</div>
					</div>`;
				})
				.join("") || `<div class="ps-muted">${__("No permitted values yet.")}</div>`
		);
	}

	accessSummaryHtml(group) {
		const doctypes = new Set((group.rules || []).map((rule) => rule.reference_doctype).filter(Boolean));
		if (!group.members.length || !doctypes.size) {
			return `<p class="ps-muted">${__("Add members and permitted values to see who can use what.")}</p>`;
		}
		return `<p>${__(
			"This group gives access to {0} users and {1} permitted values across {2} DocTypes.",
			[String(group.members.length), String(group.rules.length), String(doctypes.size)]
		)}</p>`;
	}

	usersHtml() {
		const ungrouped = this.state.ungrouped_users || [];
		const grouped = [];
		(this.state.groups || []).forEach((group) => {
			(group.members || []).forEach((member) => {
				grouped.push({ member, group });
			});
		});
		const ungroupedRows =
			ungrouped
				.map(
					(user) => `<tr>
					<td><strong>${frappehero.esc(user.full_name || user.name)}</strong><div class="ps-muted">${frappehero.esc(user.name)}</div></td>
					<td class="ps-muted">${__("No group")}</td>
					<td><button type="button" class="ps-link" data-action="add-ungrouped" data-user="${frappehero.esc(user.name)}">${__("Add to selected group")}</button></td>
				</tr>`
				)
				.join("") || `<tr><td colspan="3" class="ps-empty">${__("Every enabled user is already in a group.")}</td></tr>`;
		const groupedRows = grouped
			.map(({ member, group }) => {
				const title = group.group_name || group.name;
				return `<tr>
					<td><strong>${frappehero.esc(member.full_name || member.user)}</strong><div class="ps-muted">${frappehero.esc(member.user)}</div></td>
					<td><button type="button" class="ps-link" data-action="select-group" data-name="${frappehero.esc(group.name)}">${frappehero.esc(title)}</button></td>
					<td><span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span></td>
				</tr>`;
			})
			.join("");
		const shown = ungrouped.length;
		const total = this.state.ungrouped_total || shown;
		return `<div class="ps-panel">
			<div class="ps-panel-head"><div><h2>${__("Users without a group")}</h2><p class="ps-muted">${__("{0} shown of {1}", [String(shown), String(total)])}</p></div></div>
			<table class="ps-table"><thead><tr><th>${__("User")}</th><th>${__("Group")}</th><th></th></tr></thead><tbody>${ungroupedRows}</tbody></table>
		</div>
		<div class="ps-panel" style="margin-top:12px">
			<h2>${__("Users in a group")}</h2>
			<table class="ps-table"><thead><tr><th>${__("User")}</th><th>${__("Group")}</th><th>${__("Status")}</th></tr></thead><tbody>${groupedRows || `<tr><td colspan="3" class="ps-empty">${__("No members yet.")}</td></tr>`}</tbody></table>
		</div>`;
	}

	accessHtml() {
		const people = new Map();
		(this.state.groups || []).forEach((group) => {
			(group.members || []).forEach((member) => {
				if (!people.has(member.user)) {
					people.set(member.user, { user: member.user, full_name: member.full_name, groups: [] });
				}
				people.get(member.user).groups.push(group);
			});
		});
		(this.state.ungrouped_users || []).forEach((user) => {
			if (!people.has(user.name)) {
				people.set(user.name, { user: user.name, full_name: user.full_name, groups: [] });
			}
		});
		const options = [...people.values()].sort((a, b) => (a.full_name || a.user).localeCompare(b.full_name || b.user));
		if (!this.accessUser || !people.has(this.accessUser)) {
			this.accessUser = options.length ? options[0].user : "";
		}
		const person = people.get(this.accessUser);
		const choices = options
			.map(
				(row) =>
					`<option value="${frappehero.esc(row.user)}" ${row.user === this.accessUser ? "selected" : ""}>${frappehero.esc(row.full_name || row.user)}</option>`
			)
			.join("");
		const body = !person
			? `<div class="ps-empty">${__("No users to show.")}</div>`
			: person.groups.length
				? person.groups
						.map((group) => {
							const title = group.group_name || group.name;
							return `<div class="ps-box" style="margin-top:10px">
								<div class="ps-row-between"><strong>${frappehero.esc(title)}</strong><span class="ps-pill ${this.statusClass(group)}">${frappehero.esc(this.statusLabel(group))}</span></div>
								${this.valueRowsHtml(group.rules, group.name)}
							</div>`;
						})
						.join("")
				: `<div class="ps-empty">${__("This user is not in a permission group, so the studio grants them no values.")}</div>`;
		return `<div class="ps-panel">
			<div class="ps-panel-head"><h2>${__("View User Access")}</h2></div>
			<select class="ps-access-user ps-select">${choices}</select>
			${body}
		</div>`;
	}

	matrixHtml(group) {
		if (!group) {
			return `<div class="ps-empty">${__("Select a group to see its matrix.")}</div>`;
		}
		const matrix = group.matrix || { doctypes: [], rows: [] };
		if (!matrix.rows.length || !matrix.doctypes.length) {
			return `<div class="ps-empty">${__("Add members and permitted values to see the grid.")}</div>`;
		}
		const head = matrix.doctypes.map((doctype) => `<th>${frappehero.esc(doctype)}</th>`).join("");
		const body = matrix.rows
			.map((row) => {
				const cells = matrix.doctypes
					.map((doctype) => {
						const values = row.cells[doctype] || [];
						return `<td>${values
							.map((cell) => `<div>${frappehero.esc(cell.value)}${cell.is_default ? " ★" : ""}</div>`)
							.join("")}</td>`;
					})
					.join("");
				return `<tr><td>${frappehero.esc(row.full_name || row.user)}</td>${cells}</tr>`;
			})
			.join("");
		return `<div class="ps-matrix-wrap"><table class="ps-matrix"><thead><tr><th>${__("User")}</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
	}

	onInput(event) {
		if (!event.target.matches(".ps-top-search, .ps-table-search")) {
			return;
		}
		clearTimeout(this.searchTimer);
		const value = event.target.value || "";
		const fromTable = event.target.matches(".ps-table-search");
		this.searchTimer = setTimeout(async () => {
			this.filters.search = value;
			this.pageStart = 0;
			await this.refresh();
			if (!fromTable) {
				return;
			}
			const input = this.page.main.find(".ps-table-search").get(0);
			if (input) {
				input.focus();
				const end = input.value.length;
				input.setSelectionRange(end, end);
			}
		}, 250);
	}

	onChange(event) {
		if (event.target.matches(".ps-status")) {
			this.statusFilter = event.target.value || "all";
			this.pageStart = 0;
			this.render();
		} else if (event.target.matches(".ps-access-user")) {
			this.accessUser = event.target.value;
			this.render();
		}
	}

	onClick(event) {
		const section = event.target.closest("[data-section]");
		if (section) {
			this.section = section.dataset.section;
			this.render();
			return;
		}
		const target = event.target.closest("[data-action]");
		if (!target || target.disabled) {
			return;
		}
		const action = target.dataset.action;
		if (action === "select-group") {
			this.selected = target.dataset.name;
			if (this.section !== "overview" && this.section !== "groups") {
				this.section = "groups";
			}
			this.render();
		} else if (action === "detail-tab") {
			this.detailTab = target.dataset.tab || "overview";
			this.render();
		} else if (action === "page-go") {
			const page = Number(target.dataset.page) || 1;
			this.pageStart = Math.max(page - 1, 0) * this.pageSize;
			this.render();
		} else if (action === "refresh" || action === "sync-all") {
			if (action === "sync-all") {
				this.syncAll();
			} else {
				this.refresh();
			}
		} else if (action === "coverage") {
			frappe.set_route("query-report", "Permission Coverage");
		} else if (action === "new-group") {
			this.openGroupDialog();
		} else if (action === "edit-group") {
			this.openEditGroupDialog();
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
		} else if (action === "edit-rule") {
			this.openEditRule(target.dataset.rule, target.dataset.group);
		} else if (action === "remove-rule") {
			this.removeRule(target.dataset.rule, target.dataset.group);
		}
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
				this.section = "groups";
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
