// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("User", {
	refresh(frm) {
		if (!frm.doc.name || frm.doc.name === "Guest") {
			return;
		}

		const can_manage =
			frm.doc.name === frappe.session.user || frappe.user.has_role("System Manager");
		if (!can_manage) {
			return;
		}

		frappe.call({
			method: "logistics.integrations.outlook.api.get_connection_status",
			args: { user: frm.doc.name },
			callback(r) {
				const status = r.message || {};
				render_outlook_status(frm, status);
				add_outlook_buttons(frm, status);
			},
		});
	},
});

function render_outlook_status(frm, status) {
	const connected = status.connected ? __("Connected") : __("Not connected");
	const sync_state = status.opted_in ? __("Enabled") : __("Disabled");
	const admin_state = status.sync_enabled ? __("On") : __("Off");

	frm.set_df_property(
		"sync_erpnext_tasks_to_outlook",
		"description",
		__(
			"Outlook: {0}. User sync: {1}. System sync: {2}.",
			[connected, sync_state, admin_state]
		)
	);
}

function add_outlook_buttons(frm, status) {
	if (!status.sync_enabled) {
		return;
	}

	if (!status.connected) {
		frm.add_custom_button(__("Connect Outlook"), () => {
			frappe.call({
				method: "logistics.integrations.outlook.api.connect_outlook",
				args: { user: frm.doc.name },
				callback(r) {
					if (r.message) {
						window.location.href = r.message;
					}
				},
			});
		});
		return;
	}

	frm.add_custom_button(__("Sync Now"), () => {
		frappe.call({
			method: "logistics.integrations.outlook.api.sync_now",
			args: { user: frm.doc.name },
			callback() {
				frappe.show_alert({
					message: __("Outlook sync queued."),
					indicator: "green",
				});
			},
		});
	});

	frm.add_custom_button(__("Disconnect Outlook"), () => {
		frappe.confirm(__("Disconnect Outlook for this user?"), () => {
			frappe.call({
				method: "logistics.integrations.outlook.api.disconnect_outlook",
				args: { user: frm.doc.name },
				callback() {
					frappe.show_alert({
						message: __("Outlook disconnected."),
						indicator: "orange",
					});
					frm.reload_doc();
				},
			});
		});
	});
}
