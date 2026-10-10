// route: special-projects-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["special-projects-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Special Projects Control Tower");
};

frappe.pages["special-projects-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "special-projects-control-tower") {
		frappe.set_route("dashboard-view", "Special Projects Control Tower");
	}
};
