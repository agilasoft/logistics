frappe.ui.form.on("Sales Channel", {
	refresh(frm) {
		frm.add_custom_button(__("Connect"), () => open_connect_dialog(frm));
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Sync Orders"), () => run_sync(frm, "sync_orders"), __("Sync"));
		frm.add_custom_button(__("Sync Items"), () => run_sync(frm, "sync_items"), __("Sync"));
		frm.add_custom_button(__("Push Stock"), () => run_sync(frm, "push_stock"), __("Sync"));
	},
});

const CONNECT_PLATFORMS = [
	{
		name: "Shopee",
		login: true,
		fields: ["partner_id", "app_secret"],
		labels: { partner_id: "Partner ID", app_secret: "Partner key" },
	},
	{
		name: "Lazada",
		login: true,
		fields: ["app_key", "app_secret"],
		labels: { app_key: "App key", app_secret: "App secret" },
	},
	{
		name: "TikTok Shop",
		login: true,
		fields: ["app_key", "app_secret"],
		labels: { app_key: "App key", app_secret: "App secret" },
	},
	{
		name: "Shopify",
		login: true,
		fields: ["api_url", "app_key", "app_secret"],
		labels: { api_url: "Store domain", app_key: "Client ID", app_secret: "Client secret" },
	},
	{
		name: "Facebook",
		login: true,
		fields: ["app_key", "app_secret"],
		labels: { app_key: "App ID", app_secret: "App secret" },
	},
	{
		name: "WooCommerce",
		login: true,
		fields: ["api_url"],
		labels: { api_url: "Store URL" },
	},
	{
		name: "Pancake",
		login: false,
		fields: ["api_key"],
		labels: { api_key: "API key" },
	},
];

const CONNECT_FIELD_NAMES = ["partner_id", "app_key", "app_secret", "api_url", "api_key"];

function run_sync(frm, method) {
	frappe.call({
		method: "logistics.order_management.api." + method,
		args: { channel: frm.doc.name },
		freeze: true,
		freeze_message: __("Syncing..."),
		callback(r) {
			if (r.message) {
				frappe.show_alert({ message: r.message, indicator: "green" });
			}
			frm.reload_doc();
		},
		error() {
			frm.reload_doc();
		},
	});
}

function open_connect_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Connect"),
		fields: [
			{
				fieldname: "intro",
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					"Log in on the platform. This screen does not ask for the marketplace password."
				)}</p><div class="om-connect-platforms"></div>`,
			},
			{ fieldname: "platform", fieldtype: "Data", hidden: 1 },
			{ fieldname: "partner_id", fieldtype: "Data", label: __("Partner ID") },
			{ fieldname: "app_key", fieldtype: "Data", label: __("App key") },
			{ fieldname: "app_secret", fieldtype: "Password", label: __("App secret") },
			{ fieldname: "api_url", fieldtype: "Data", label: __("API URL") },
			{ fieldname: "api_key", fieldtype: "Password", label: __("API key") },
		],
		primary_action_label: __("Log in"),
		primary_action(values) {
			begin_connect(frm, dialog, values);
		},
	});
	dialog.show();
	render_platform_buttons(frm, dialog);
	select_platform(frm, dialog, frm.doc.platform || "Shopee");
}

function render_platform_buttons(frm, dialog) {
	const wrap = dialog.fields_dict.intro.$wrapper.find(".om-connect-platforms");
	wrap.empty();
	CONNECT_PLATFORMS.forEach((platform) => {
		const button = $(
			`<button type="button" class="btn btn-default btn-sm" style="margin: 0 6px 6px 0;"></button>`
		);
		button.text(platform.name);
		button.attr("data-platform", platform.name);
		button.on("click", () => select_platform(frm, dialog, platform.name));
		wrap.append(button);
	});
}

function select_platform(frm, dialog, name) {
	const platform = CONNECT_PLATFORMS.find((row) => row.name === name) || CONNECT_PLATFORMS[0];
	dialog.set_value("platform", platform.name);
	dialog.fields_dict.intro.$wrapper.find("button").each(function () {
		const active = $(this).attr("data-platform") === platform.name;
		$(this).toggleClass("btn-primary", active).toggleClass("btn-default", !active);
	});
	CONNECT_FIELD_NAMES.forEach((field) => {
		const show = platform.fields.includes(field);
		dialog.set_df_property(field, "hidden", show ? 0 : 1);
		if (platform.labels[field]) {
			dialog.set_df_property(field, "label", __(platform.labels[field]));
		}
		if (show && !dialog.get_value(field)) {
			const current = frm.doc[field];
			if (current && field !== "app_secret" && field !== "api_key") {
				dialog.set_value(field, current);
			}
		}
	});
	dialog.set_primary_action_label(platform.login ? __("Log in to {0}", [platform.name]) : __("Find shops"));
}

function begin_connect(frm, dialog, values) {
	const platform = CONNECT_PLATFORMS.find((row) => row.name === values.platform);
	if (!platform) {
		frappe.msgprint(__("Choose a platform"));
		return;
	}
	const credentials = { platform: platform.name };
	for (const field of platform.fields) {
		if (!values[field]) {
			frappe.msgprint(__("Enter {0}", [platform.labels[field] || field]));
			return;
		}
		credentials[field] = values[field];
		frm.set_value(field, values[field]);
	}
	frm.set_value("platform", platform.name);
	if (platform.name === "Pancake") {
		frappe.call({
			method: "logistics.order_management.connect.list_pancake_shops",
			args: { api_key: credentials.api_key, api_url: values.api_url || "" },
			freeze: true,
			freeze_message: __("Finding shops..."),
			callback(r) {
				if (r.message) {
					dialog.hide();
					apply_connect_result(frm, r.message);
				}
			},
		});
		return;
	}
	frappe.call({
		method: "logistics.order_management.connect.start_connect",
		args: { platform: platform.name, credentials },
		freeze: true,
		freeze_message: __("Opening {0}...", [platform.name]),
		callback(r) {
			const message = r.message || {};
			if (!message.authorize_url) {
				return;
			}
			const popup = window.open(
				message.authorize_url,
				"order-management-connect",
				"width=640,height=760"
			);
			if (!popup) {
				frappe.msgprint(__("Allow pop-ups to log in on {0}.", [platform.name]));
				return;
			}
			dialog.hide();
			listen_for_connect(frm, message.state);
		},
	});
}

function listen_for_connect(frm, state) {
	function on_message(event) {
		if (event.origin !== window.location.origin) {
			return;
		}
		const data = event.data || {};
		if (data.source !== "order-management-connect") {
			return;
		}
		const payload = data.payload || {};
		if (payload.pending) {
			poll_connect_result(frm, payload.state || state, 0);
			return;
		}
		window.removeEventListener("message", on_message);
		if (!payload.ok) {
			frappe.msgprint(payload.error || __("Could not connect"));
			return;
		}
		apply_connect_result(frm, payload);
	}
	window.addEventListener("message", on_message);
}

function poll_connect_result(frm, state, tries) {
	frappe.call({
		method: "logistics.order_management.connect.connect_result",
		args: { state },
		callback(r) {
			const payload = r.message || {};
			if (payload.pending && tries < 8) {
				setTimeout(() => poll_connect_result(frm, state, tries + 1), 1000);
				return;
			}
			if (!payload.ok) {
				frappe.msgprint(payload.error || __("Could not connect"));
				return;
			}
			apply_connect_result(frm, payload);
		},
	});
}

function apply_connect_result(frm, payload) {
	const fields = Object.assign({}, payload.fields || {});
	const choices = payload.choices || [];
	if (choices.length > 1) {
		choose_connect_account(frm, fields, choices);
		return;
	}
	if (choices.length === 1) {
		Object.assign(fields, choices[0].fields || {});
	}
	write_connect_fields(frm, fields);
}

function choose_connect_account(frm, fields, choices) {
	const dialog = new frappe.ui.Dialog({
		title: __("Choose a shop"),
		fields: [
			{
				fieldname: "choice",
				fieldtype: "Select",
				label: __("Shop"),
				options: choices.map((choice) => choice.label).join("\n"),
				reqd: 1,
			},
		],
		primary_action_label: __("Use this shop"),
		primary_action(values) {
			const picked = choices.find((choice) => choice.label === values.choice) || choices[0];
			write_connect_fields(frm, Object.assign({}, fields, picked.fields || {}));
			dialog.hide();
		},
	});
	dialog.show();
}

function write_connect_fields(frm, fields) {
	Object.keys(fields).forEach((field) => {
		const value = fields[field];
		if (value === undefined || value === null || value === "") {
			return;
		}
		if (field === "channel_name" && frm.doc.channel_name) {
			return;
		}
		frm.set_value(field, value);
	});
	frappe.show_alert({
		message: __("Connection details added. Save the Sales Channel."),
		indicator: "green",
	});
}
