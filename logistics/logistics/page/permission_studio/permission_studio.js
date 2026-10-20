// route: permission-studio
// Thin stub. The workspace lives in public/js/permission_studio_page.js.

frappe.provide("logistics.permission_studio");

frappe.pages["permission-studio"].on_page_load = function (wrapper) {
	const ns = logistics.permission_studio;
	const start = function () {
		if (!ns.page && ns.PermissionStudioPage) {
			ns.page = new ns.PermissionStudioPage(wrapper);
		}
	};
	if (ns.PermissionStudioPage) {
		start();
		return;
	}
	frappe.require(
		[
			"/assets/logistics/js/permission_studio_picker.js?v=1",
			"/assets/logistics/css/permission_studio.css?v=1",
			"/assets/logistics/js/permission_studio_page.js?v=1",
		],
		start
	);
};

frappe.pages["permission-studio"].on_page_show = function () {
	const page = logistics.permission_studio.page;
	if (page && page.refresh) {
		page.refresh();
	}
};
