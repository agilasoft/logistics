// route: air-freight-control-tower
// Thin stub — UI lives in public/js/air_freight_control_tower_page.js (hooks page_js).
// rev: 2026-07-24-hooks-stub

frappe.provide("logistics.air_freight_control_tower");

frappe.pages["air-freight-control-tower"].on_page_load = function (wrapper) {
	const ns = logistics.air_freight_control_tower;
	if (ns.page) {
		return;
	}
	if (ns.AirFreightControlTowerPage) {
		ns.page = new ns.AirFreightControlTowerPage(wrapper);
		return;
	}
	// Fallback if page_js asset has not assigned the class yet.
	frappe.require("/assets/logistics/js/air_freight_control_tower_page.js", function () {
		if (!ns.page && ns.AirFreightControlTowerPage) {
			ns.page = new ns.AirFreightControlTowerPage(wrapper);
		}
	});
};

frappe.pages["air-freight-control-tower"].on_page_show = function () {
	const page = logistics.air_freight_control_tower.page;
	if (page && page.refresh) {
		page.refresh();
	}
};
