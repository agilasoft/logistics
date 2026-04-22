// Copyright (c) 2026, AgilaSoft and contributors
// See license.txt

frappe.ui.form.on("Air Consolidation Plan", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Fetch matching shipments"), () => {
				frappe.call({
					method: "fetch_matching_air_shipments",
					doc: frm.doc,
					freeze: true,
					callback(r) {
						if (r.exc) {
							return;
						}
						frm.reload_doc();
						const d = r.message || {};
						const added = (d.added || []).length;
						const already = (d.already_present || []).length;
						const skipped = (d.skipped || []).length;
						const parts = [];
						if (added) {
							parts.push(__("{0} added", [String(added)]));
						}
						if (already) {
							parts.push(__("{0} already on plan", [String(already)]));
						}
						if (skipped) {
							parts.push(__("{0} skipped", [String(skipped)]));
						}
						frappe.msgprint(parts.join(", ") || __("No matching shipments found."));
					},
				});
			});
		}
		if (frm.doc.docstatus === 1) {
			const all_linked = (frm.doc.items || []).every((r) => r.linked_air_consolidation);
			if (!all_linked) {
				frm.add_custom_button(__("Create Air Consolidation"), () => {
					frappe.call({
						method: "create_air_consolidation_from_plan",
						doc: frm.doc,
						freeze: true,
						callback(r) {
							if (!r.exc && r.message) {
								frappe.set_route("Form", "Air Consolidation", r.message);
							}
						},
					});
				});
			}
		}
	},
});
