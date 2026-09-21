// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
//
// User Quick Entry only collects email / first name / role profile. Saving that dialog
// without roles turns the user into a Website User with no desk access. Always open the
// full User form so roles, password, and modules can be set before the first save.

frappe.provide("frappe.ui.form");

if (frappe.ui.form.QuickEntryForm) {
	frappe.ui.form.UserQuickEntryForm = class UserQuickEntryForm extends frappe.ui.form.QuickEntryForm {
		is_quick_entry() {
			return false;
		}
	};
}
