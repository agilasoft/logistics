// route: sea-freight-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["sea-freight-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Sea Freight Control Tower");
};

frappe.pages["sea-freight-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "sea-freight-control-tower") {
		frappe.set_route("dashboard-view", "Sea Freight Control Tower");
	}
};
