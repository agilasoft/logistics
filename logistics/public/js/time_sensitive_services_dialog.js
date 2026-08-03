// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Time Sensitive Case → Manage Linked Services dialog.
 * Thin wrapper around logistics.show_linked_services_dialog.
 */
frappe.provide("logistics.time_sensitive");

const TS_SERVICES_API =
	"logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case";

logistics.time_sensitive.show_services_dialog = function (frm) {
	function open() {
		if (!logistics.show_linked_services_dialog) {
			frappe.msgprint({
				message: __(
					"Services dialog failed to load. Hard-refresh the page (Ctrl+Shift+R)."
				),
				indicator: "orange",
			});
			return;
		}
		logistics.show_linked_services_dialog(frm, {
			listMethod: TS_SERVICES_API + ".list_case_linked_services",
			addMethod: TS_SERVICES_API + ".add_linked_service",
			removeMethod: TS_SERVICES_API + ".remove_linked_service",
			parentField: "case_name",
			parentLabel: __("Case"),
			allowEdit: true,
			emptyHint: __("Add a service type above to link it to this case."),
			addHint: __(
				"Select a service type to link to this case. You can add multiple services of the same type (e.g. international and domestic Sea)."
			),
			unsavedMessage: __(
				"Save the Time Sensitive Case before managing services."
			),
			removeConfirm: (ls) =>
				__("Remove linked service {0} from this case?", [
					`<strong>${frappe.utils.escape_html(ls)}</strong>`,
				]),
		});
	}

	if (logistics.show_linked_services_dialog) {
		open();
		return;
	}
	frappe.require("/assets/logistics/js/linked_services_dialog.js", open);
};
