// route: pricing-center-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["pricing-center-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Pricing Center Control Tower");
};

frappe.pages["pricing-center-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "pricing-center-control-tower") {
		frappe.set_route("dashboard-view", "Pricing Center Control Tower");
	}
};
