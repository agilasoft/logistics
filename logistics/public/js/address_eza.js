// Address EZA: show/require Economic Zone only when EZA is on; clear zone when toggled off.

frappe.ui.form.on("Address", {
	custom_eza(frm) {
		if (!frm.doc.custom_eza && frm.doc.custom_economic_zone) {
			frm.set_value("custom_economic_zone", null);
		}
	},
});
