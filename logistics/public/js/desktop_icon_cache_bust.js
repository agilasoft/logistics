// Force logistics desktop icons (Warehousing, Transport) to use our SVGs
(function () {
	const _get_desktop_icon = frappe.utils.get_desktop_icon;
	if (_get_desktop_icon) {
		frappe.utils.get_desktop_icon = function (icon_name, variant) {
			const icon_data = frappe.utils.get_desktop_icon_by_label(icon_name);
			// Always return our icon URL for logistics app (bypass boot list check)
			if (icon_data && icon_data.app === "logistics" && icon_name) {
				variant = (variant || "solid").toLowerCase();
				const path =
					"/assets/logistics/icons/desktop_icons/" +
					variant +
					"/" +
					frappe.scrub(icon_name) +
					".svg?v=2";
				return path;
			}
			return _get_desktop_icon.apply(this, arguments);
		};
	}
})();
