// Force logistics desktop icons and workspace sidebars to use SVGs from
// public/icons/desktop_icons/ (same location as other logistics modules).
(function () {
	frappe.ready(function () {
		const _get_desktop_icon = frappe.utils.get_desktop_icon;
		if (_get_desktop_icon) {
			frappe.utils.get_desktop_icon = function (icon_name, variant) {
				if (icon_name) {
					variant = (variant || "solid").toLowerCase();
					const scrubbed = frappe.scrub(icon_name);
					const url =
						"assets/logistics/icons/desktop_icons/" + variant + "/" + scrubbed + ".svg";
					const urls = frappe.boot.desktop_icon_urls?.logistics?.[variant];
					if (urls && urls.includes(url)) {
						return "/" + url;
					}
					const icon_data = frappe.utils.get_desktop_icon_by_label(icon_name);
					if (icon_data && icon_data.app === "logistics") {
						return "/" + url;
					}
				}
				return _get_desktop_icon.apply(this, arguments);
			};
		}

		// Sidebar header: use logistics SVG for workspace icon even when not on desktop
		if (frappe.ui.SidebarHeader && frappe.ui.SidebarHeader.prototype.set_header_icon) {
			const _set_header_icon = frappe.ui.SidebarHeader.prototype.set_header_icon;
			frappe.ui.SidebarHeader.prototype.set_header_icon = function () {
				const sidebar_data = this.sidebar?.sidebar_data;
				const title = this.sidebar?.sidebar_title;
				if (sidebar_data?.app === "logistics" && title) {
					const icon_url = frappe.utils.get_desktop_icon(title, "solid");
					if (icon_url) {
						this.header_icon = `<img src=${icon_url}></img>`;
						return;
					}
				}
				return _set_header_icon.apply(this, arguments);
			};
		}
	});
})();
