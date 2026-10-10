// route: warehousing-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["warehousing-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Warehousing Control Tower");
};

frappe.pages["warehousing-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "warehousing-control-tower") {
		frappe.set_route("dashboard-view", "Warehousing Control Tower");
	}
};
