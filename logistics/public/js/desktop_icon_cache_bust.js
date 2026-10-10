// Logistics desktop SVGs under public/icons/desktop_icons/ still back the
// fallback icon grid. The apps-screen dock and sidebar header draw Lucide
// marks from the Dock and Sidebar fixtures, so this does not replace
// SidebarHeader.set_header_icon.
(function () {
	function run() {
		if (typeof frappe === "undefined" || !frappe.utils) return;
		const _get_desktop_icon = frappe.utils.get_desktop_icon;
		if (_get_desktop_icon) {
			frappe.utils.get_desktop_icon = function (icon_name, variant) {
				if (icon_name) {
					variant = (variant || "solid").toLowerCase();
					const scrubbed = frappe.scrub(icon_name);
					const url =
						"assets/logistics/icons/desktop_icons/" + variant + "/" + scrubbed + ".svg";
					const urls = frappe.boot?.desktop_icon_urls?.logistics?.[variant];
					if (urls && urls.includes(url)) {
						return "/" + url;
					}
					const icon_data = frappe.utils.get_desktop_icon_by_label?.(icon_name);
					if (icon_data && icon_data.app === "logistics") {
						return "/" + url;
					}
				}
				return _get_desktop_icon.apply(this, arguments);
			};
		}
	}

	function tryRun() {
		if (typeof frappe !== "undefined" && frappe.utils) {
			run();
		} else {
			setTimeout(tryRun, 50);
		}
	}
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", tryRun);
	} else {
		tryRun();
	}
})();
