frappe.ui.form.on("Sales Channel", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}
		frm.add_custom_button(__("Sync Orders"), () => run_sync(frm, "sync_orders"), __("Sync"));
		frm.add_custom_button(__("Sync Items"), () => run_sync(frm, "sync_items"), __("Sync"));
		frm.add_custom_button(__("Push Stock"), () => run_sync(frm, "push_stock"), __("Sync"));
	},
});

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
