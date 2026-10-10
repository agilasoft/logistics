// route: customs-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["customs-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Customs Control Tower");
};

frappe.pages["customs-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "customs-control-tower") {
		frappe.set_route("dashboard-view", "Customs Control Tower");
	}
};
