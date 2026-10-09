// route: sustainability-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["sustainability-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Sustainability Control Tower");
};

frappe.pages["sustainability-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "sustainability-control-tower") {
		frappe.set_route("dashboard-view", "Sustainability Control Tower");
	}
};
