// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
//
// Frappe hides the Roles section on a new User until after the first save. Saving without
// roles creates a Website User who cannot open CargoNext. Show Role Profile / roles on
// the new form so they can be assigned before insert.

frappe.ui.form.on("User", {
	refresh(frm) {
		show_roles_section_on_new_user(frm);
	},
	validate(frm) {
		block_system_user_save_without_roles(frm);
	},
});

function show_roles_section_on_new_user(frm) {
	if (!frm.is_new() || !frm.can_edit_roles) {
		return;
	}
	if (!["System User", "Website User"].includes(frm.doc.user_type || "System User")) {
		return;
	}

	frm.toggle_display("sb1", true);
	ensure_new_user_roles_editor(frm);

	if (frm.dashboard && typeof frm.dashboard.set_headline === "function") {
		frm.dashboard.set_headline(
			__(
				"Assign a Role Profile or roles before saving. Saving without roles creates a Website User with no desk access."
			)
		);
	}
}

function block_system_user_save_without_roles(frm) {
	if (!frm.is_new()) {
		return;
	}
	if (!frm.can_edit_roles) {
		return;
	}
	if (frm.doc.user_type && frm.doc.user_type !== "System User") {
		return;
	}
	if (frm.roles_editor) {
		frm.roles_editor.set_roles_in_table();
	}

	const has_profiles = (frm.doc.role_profiles || []).some((row) => row.role_profile);
	const has_roles = (frm.doc.roles || []).some((row) => row.role);
	if (!has_profiles && !has_roles) {
		frappe.throw(
			__(
				"Assign a Role Profile or at least one role before saving. Saving without roles creates a Website User with no desk access."
			)
		);
	}
}

function ensure_new_user_roles_editor(frm) {
	if (frm.roles_editor || !frm.fields_dict.roles_html) {
		return;
	}

	const role_area = $('<div class="role-editor">').appendTo(frm.fields_dict.roles_html.wrapper);
	frm.roles_editor = new frappe.RoleEditor(
		role_area,
		frm,
		frm.doc.role_profiles && frm.doc.role_profiles.length ? 1 : 0
	);
}
