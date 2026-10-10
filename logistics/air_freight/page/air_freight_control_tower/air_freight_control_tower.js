// route: air-freight-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["air-freight-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Air Freight Control Tower");
};

frappe.pages["air-freight-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "air-freight-control-tower") {
		frappe.set_route("dashboard-view", "Air Freight Control Tower");
	}
};
