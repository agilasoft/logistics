// route: mice-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["mice-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "MICE Control Tower");
};

frappe.pages["mice-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "mice-control-tower") {
		frappe.set_route("dashboard-view", "MICE Control Tower");
	}
};
