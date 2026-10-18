frappe.ui.form.on("Item Group", {
	refresh(frm) {
		if (frm.is_new() || !frappe.model.can_write("Item")) {
			return;
		}
		frm.page.add_action_item(__("Apply GL Accounts to Items"), () => {
			frappe.confirm(
				__(
					"Copy GL accounts from this Item Group onto every Item in this group and its child groups, for each company set on Item Defaults?"
				),
				() => {
					frappe.call({
						method: "logistics.utils.item_accounts.apply_gl_accounts_to_items",
						args: { item_group: frm.doc.name },
						freeze: true,
						freeze_message: __("Applying GL accounts..."),
						callback(r) {
							const msg = (r && r.message) || {};
							const companies = msg.companies || [];
							frappe.msgprint({
								title: __("GL Accounts Applied"),
								indicator: "green",
								message: __("{0} of {1} items updated across {2} companies.").format(
									msg.updated || 0,
									msg.items || 0,
									companies.length
								),
							});
						},
					});
				}
			);
		});
	},
});
