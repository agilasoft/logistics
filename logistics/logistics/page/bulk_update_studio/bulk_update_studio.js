// route: bulk-update-studio
// Thin stub — UI lives in public/js/bulk_update_studio_page.js (hooks page_js).

frappe.provide("logistics.bulk_update_studio");

frappe.pages["bulk-update-studio"].on_page_load = function (wrapper) {
	const ns = logistics.bulk_update_studio;
	if (ns.page) {
		return;
	}
	if (ns.BulkUpdateStudioPage) {
		ns.page = new ns.BulkUpdateStudioPage(wrapper);
		return;
	}
	frappe.require("/assets/logistics/js/bulk_update_studio_page.js?v=1", function () {
		if (!ns.page && ns.BulkUpdateStudioPage) {
			ns.page = new ns.BulkUpdateStudioPage(wrapper);
		}
	});
};

frappe.pages["bulk-update-studio"].on_page_show = function () {
	const page = logistics.bulk_update_studio.page;
	if (page && page.refresh) {
		page.refresh();
	}
};
