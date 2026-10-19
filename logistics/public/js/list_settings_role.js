// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
//
// Frappe shows List Settings only to System Manager. Roles listed on
// Logistics Settings get the same menu item. Saving is checked on the server.

(function () {
	function patch_list_settings_menu() {
		var ListView = frappe.views && frappe.views.ListView;
		if (!ListView || !ListView.prototype) {
			return false;
		}
		if (ListView.prototype._logisticsListSettingsPatched) {
			return true;
		}
		var original = ListView.prototype.get_menu_items;
		ListView.prototype.get_menu_items = function () {
			var items = original.apply(this, arguments) || [];
			if (!frappe.boot || !frappe.boot.can_edit_list_settings) {
				return items;
			}
			var label = __("List Settings", null, "Button in list view menu");
			var present = items.some(function (item) {
				return item && item.label === label;
			});
			if (!present && typeof this.get_view_settings === "function") {
				items.push(this.get_view_settings());
			}
			return items;
		};
		ListView.prototype._logisticsListSettingsPatched = true;
		return true;
	}

	function install() {
		if (patch_list_settings_menu()) {
			return;
		}
		// This file can load before the desk bundle defines ListView.
		var tries = 0;
		var timer = setInterval(function () {
			tries += 1;
			if (patch_list_settings_menu() || tries > 50) {
				clearInterval(timer);
			}
		}, 200);
	}

	install();
})();
