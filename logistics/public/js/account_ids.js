// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Menu action on the Account list and Chart of Accounts tree. Rebuilds
// document IDs that no longer match account number, account name, and the
// company abbreviation.

frappe.provide("logistics.accounts");

logistics.accounts.prompt_account_id_update = function (opts) {
	opts = opts || {};
	if (!frappe.model.can_write("Account")) {
		frappe.msgprint(__("You need write permission on Account to update IDs."));
		return;
	}
	frappe.call({
		method: "logistics.logistics.account_ids.update_account_ids",
		args: { company: opts.company || null, apply: 0 },
		freeze: true,
		freeze_message: __("Checking Account IDs..."),
		callback(response) {
			if (response.exc) {
				return;
			}
			logistics.accounts.show_account_id_update(response.message || {}, opts);
		},
	});
};

logistics.accounts.show_account_id_update = function (plan, opts) {
	const updates = plan.updates || [];
	const skipped = plan.skipped || [];
	const collisions = plan.collisions || [];
	if (collisions.length) {
		const lines = collisions.slice(0, 20).map((row) => {
			const text =
				row.reason === "duplicate"
					? __("{0} and {1} would both become {2}", [row.from, row.existing, row.to])
					: __("{0} would become {1}, already used by {2}", [row.from, row.to, row.existing]);
			return frappe.utils.escape_html(text);
		});
		frappe.msgprint({
			title: __("Account ID already exists"),
			indicator: "red",
			message: lines.join("<br>"),
		});
		return;
	}
	if (!updates.length) {
		const message = skipped.length
			? __("{0} accounts need an ID, and it cannot be built from the current name.", [skipped.length])
			: __("All Account IDs already match the current naming rule.");
		frappe.msgprint({ title: __("Update Account IDs"), message: message });
		return;
	}

	const scope = opts.company
		? __("Company: {0}", [frappe.utils.escape_html(opts.company)])
		: __("All companies");
	const preview = updates
		.slice(0, 50)
		.map(
			(row) =>
				`<tr><td>${frappe.utils.escape_html(row.from)}</td><td>${frappe.utils.escape_html(row.to)}</td></tr>`
		)
		.join("");
	const more =
		updates.length > 50
			? `<p class="text-muted">${__("And {0} more.", [updates.length - 50])}</p>`
			: "";
	const skipped_note = skipped.length
		? `<p class="text-muted">${__("{0} accounts were skipped because the new ID cannot be built.", [skipped.length])}</p>`
		: "";
	const dialog = new frappe.ui.Dialog({
		title: __("Update Account IDs"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "preview",
				options: `
					<p>${scope}</p>
					<p>${__(
						"The ID is the account number, account name, and company abbreviation, separated by ' - '. Accounts without a number leave the number out."
					)}</p>
					<p>${__(
						"Linked documents are updated to the new ID. The rename runs in the background so this page does not time out."
					)}</p>
					<table class="table table-bordered table-sm">
						<thead><tr><th>${__("Current ID")}</th><th>${__("New ID")}</th></tr></thead>
						<tbody>${preview}</tbody>
					</table>
					${more}
					${skipped_note}
				`,
			},
		],
		primary_action_label: __("Update"),
		primary_action() {
			dialog.hide();
			logistics.accounts.watch_account_id_update(opts);
			frappe.call({
				method: "logistics.logistics.account_ids.update_account_ids",
				args: { company: opts.company || null, apply: 1 },
				freeze: true,
				freeze_message: __("Queueing Account ID update..."),
				callback(response) {
					if (response.exc) {
						return;
					}
					const message = response.message || {};
					if (message.already_queued) {
						frappe.show_alert({
							message: __("An Account ID update is already running."),
							indicator: "orange",
						});
						return;
					}
					if (message.queued) {
						frappe.show_alert({
							message: __("Updating {0} Account IDs in the background.", [message.count || 0]),
							indicator: "blue",
						});
					}
				},
			});
		},
	});
	dialog.show();
};

logistics.accounts.watch_account_id_update = function (opts) {
	if (logistics.accounts._account_id_listener) {
		logistics.accounts._account_id_refresh = opts || {};
		return;
	}
	logistics.accounts._account_id_listener = true;
	logistics.accounts._account_id_refresh = opts || {};
	frappe.realtime.on("logistics_account_ids_updated", (data) => {
		const refresh = logistics.accounts._account_id_refresh || {};
		const company = data && data.company;
		if (refresh.company && company && refresh.company !== company) {
			return;
		}
		if (data && data.indicator === "red") {
			return;
		}
		if (refresh.on_success) {
			refresh.on_success();
		}
	});
};

function logistics_account_list_company(listview) {
	const filters = (listview.filter_area && listview.filter_area.get()) || [];
	for (const filter of filters) {
		const parts = filter || [];
		const field = parts.length >= 4 ? parts[1] : parts[0];
		const operator = parts.length >= 4 ? parts[2] : parts[1];
		const value = parts.length >= 4 ? parts[3] : parts[2];
		if (field === "company" && operator === "=" && value) {
			return value;
		}
	}
	return null;
}

frappe.listview_settings["Account"] = frappe.listview_settings["Account"] || {};
(() => {
	const settings = frappe.listview_settings["Account"];
	const previous = settings.onload;
	settings.onload = function (listview) {
		if (previous) {
			previous.apply(this, arguments);
		}
		if (listview.__logistics_account_ids || !frappe.model.can_write("Account")) {
			return;
		}
		listview.__logistics_account_ids = true;
		listview.page.add_menu_item(__("Update Account IDs"), () => {
			logistics.accounts.prompt_account_id_update({
				company: logistics_account_list_company(listview),
				on_success() {
					listview.refresh();
				},
			});
		});
	};
})();

(() => {
	const settings = frappe.treeview_settings && frappe.treeview_settings["Account"];
	if (!settings) {
		return;
	}
	settings.menu_items = settings.menu_items || [];
	if (settings.menu_items.some((item) => item._logistics_account_ids)) {
		return;
	}
	settings.menu_items.push({
		_logistics_account_ids: true,
		label: __("Update Account IDs"),
		condition() {
			return frappe.model.can_write("Account");
		},
		action() {
			const company = settings.treeview?.page?.fields_dict?.company?.get_value() || null;
			if (!company) {
				frappe.msgprint(__("Select a Company first."));
				return;
			}
			logistics.accounts.prompt_account_id_update({
				company,
				on_success() {
					const treeview = frappe.views?.trees?.["Account"];
					if (treeview && treeview.make_tree) {
						treeview.make_tree();
					}
				},
			});
		},
	});
})();
