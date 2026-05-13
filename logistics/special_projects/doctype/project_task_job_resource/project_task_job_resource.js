// Copyright (c) 2026, Agilasoft and contributors
// Clear Resource link when category changes so link_filters stay valid.

frappe.ui.form.on("Project Task Job Resource", {
	resource_category(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "resource_name", null);
	},
});
