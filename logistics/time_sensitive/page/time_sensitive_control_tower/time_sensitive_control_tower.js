// route: time-sensitive-control-tower
// Bookmarks to the old custom page open the native Dashboard.

frappe.pages["time-sensitive-control-tower"].on_page_load = function () {
	frappe.set_route("dashboard-view", "Time Sensitive Control Tower");
};

frappe.pages["time-sensitive-control-tower"].on_page_show = function () {
	if ((frappe.get_route() || [])[0] === "time-sensitive-control-tower") {
		frappe.set_route("dashboard-view", "Time Sensitive Control Tower");
	}
};
