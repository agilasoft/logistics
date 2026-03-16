// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Milestone Template", {
	applies_to_doctype: function (frm) {
		refresh_milestone_item_field_options(frm);
	},
	refresh: function (frm) {
		refresh_milestone_item_field_options(frm);
	},
});

function refresh_milestone_item_field_options(frm) {
	var doctype = frm.doc.applies_to_doctype;
	if (!doctype) {
		set_items_field_options(frm, "", "");
		return;
	}
	frappe.call({
		method: "logistics.document_management.api.get_doctype_fields_for_milestone",
		args: { doctype: doctype },
		callback: function (r) {
			if (r.message && Array.isArray(r.message) && r.message.length) {
				var opts = r.message.join("\n");
				set_items_field_options(frm, opts, opts);
			} else {
				set_items_field_options(frm, "", "");
			}
		},
	});
}

function set_items_field_options(frm, trigger_options, sync_options) {
	if (!frm.fields_dict || !frm.fields_dict.items || !frm.fields_dict.items.grid) {
		return;
	}
	var grid = frm.fields_dict.items.grid;
	grid.update_docfield_property("trigger_field", "options", trigger_options || "");
	grid.update_docfield_property("sync_parent_date_field", "options", sync_options || "");
}
