// route: high-value-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["high-value-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "High Value Control Tower");
};

frappe.pages["high-value-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "high-value-control-tower") {
		frappe.set_route("dashboard-view", "High Value Control Tower");
	}
};
