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
	// Do not append ?v=… to these paths. Frappe AssetManager.extn() keeps the
	// query string and then looks up a loader for "v=1", which throws and
	// leaves the page blank. Cache-busting is added by frappe.require itself.
	frappe.require(
		[
			"/assets/logistics/js/permission_studio_picker.js",
			"/assets/logistics/css/permission_studio.css",
			"/assets/logistics/js/permission_studio_page.js",
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
