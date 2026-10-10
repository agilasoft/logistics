// route: transport-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["transport-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Transport Control Tower");
};

frappe.pages["transport-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "transport-control-tower") {
		frappe.set_route("dashboard-view", "Transport Control Tower");
	}
};
