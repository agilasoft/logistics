// route: sea-freight-control-tower
// Thin stub — UI lives in public/js/sea_freight_control_tower_page.js (hooks page_js).
// rev: 2026-07-24-sfct-stub

frappe.provide("logistics.sea_freight_control_tower");

frappe.pages["sea-freight-control-tower"].on_page_load = function (wrapper) {
	const ns = logistics.sea_freight_control_tower;
	if (ns.page) {
		return;
	}
	if (ns.SeaFreightControlTowerPage) {
		ns.page = new ns.SeaFreightControlTowerPage(wrapper);
		return;
	}
	frappe.require("/assets/logistics/js/sea_freight_control_tower_page.js", function () {
		if (!ns.page && ns.SeaFreightControlTowerPage) {
			ns.page = new ns.SeaFreightControlTowerPage(wrapper);
		}
	});
};

frappe.pages["sea-freight-control-tower"].on_page_show = function () {
	const page = logistics.sea_freight_control_tower.page;
	if (page && page.refresh) {
		page.refresh();
	}
};
