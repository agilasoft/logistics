// The programme tile is MICE. A Desktop Icon or saved layout can still say
// Exhibits; the grid draws that label, and without an app it falls back to the
// letter E. Rewrite both copies before the desktop page renders.
(function () {
	var EXHIBITS = "Exhibits";
	var MICE = "MICE";
	var APP = "logistics";

	function isMice(icon) {
		return icon.label === MICE || icon.link_to === MICE || icon.name === MICE;
	}

	function isExhibits(icon) {
		return icon.label === EXHIBITS || icon.link_to === EXHIBITS || icon.name === EXHIBITS;
	}

	function treeHasMice(icons) {
		return (icons || []).some(function (icon) {
			if (!icon || typeof icon !== "object") return false;
			if (isMice(icon)) return true;
			return treeHasMice(icon.child_icons);
		});
	}

	function stamp(icon) {
		if (!icon.app) icon.app = APP;
		return icon;
	}

	function shellExists(name) {
		var all = (window.frappe && frappe.boot && frappe.boot.module_sidebars) || {};
		if (all[name]) return true;
		return Object.keys(all).some(function (key) {
			var entry = all[key];
			return entry && (entry.module === name || entry.title === name || entry.name === name);
		});
	}

	function asMice(icon) {
		var keepExhibitsRoute = shellExists(EXHIBITS) && !shellExists(MICE);
		if (icon.label === EXHIBITS) icon.label = MICE;
		if (icon.link_to === EXHIBITS && !keepExhibitsRoute) icon.link_to = MICE;
		if (icon.name === EXHIBITS) icon.name = MICE;
		if (icon.module === EXHIBITS && !keepExhibitsRoute) icon.module = MICE;
		else if (!icon.module && keepExhibitsRoute) icon.module = EXHIBITS;
		return stamp(icon);
	}

	function relabel(icons, micePresent) {
		if (!Array.isArray(icons)) return icons;
		if (micePresent === undefined) micePresent = treeHasMice(icons);
		var result = [];
		icons.forEach(function (icon) {
			if (!icon || typeof icon !== "object") {
				result.push(icon);
				return;
			}
			if (micePresent && isExhibits(icon)) return;
			var updated = Object.assign({}, icon);
			if (Array.isArray(updated.child_icons)) {
				updated.child_icons = relabel(updated.child_icons, micePresent);
			}
			if (isExhibits(updated)) updated = asMice(updated);
			else if (isMice(updated)) updated = stamp(updated);
			result.push(updated);
		});
		return result;
	}

	function applyBoot() {
		if (!window.frappe || !frappe.boot || !Array.isArray(frappe.boot.desktop_icons)) return;
		frappe.boot.desktop_icons = relabel(frappe.boot.desktop_icons);
	}

	function patchArrange() {
		if (!window.frappe || !frappe.desktop_utils || !frappe.desktop_utils.arrange_layout) {
			return false;
		}
		if (frappe.desktop_utils.arrange_layout.__mice_desk) return true;
		var orig = frappe.desktop_utils.arrange_layout;
		var wrapped = function (layout, bootIcons) {
			applyBoot();
			var nextBoot = relabel(
				bootIcons || (frappe.boot && frappe.boot.desktop_icons) || []
			);
			if (frappe.boot) frappe.boot.desktop_icons = nextBoot;
			return orig(relabel(layout), nextBoot);
		};
		wrapped.__mice_desk = true;
		frappe.desktop_utils.arrange_layout = wrapped;
		return true;
	}

	function watch() {
		applyBoot();
		if (patchArrange()) return;
		var tries = 0;
		var timer = setInterval(function () {
			tries += 1;
			applyBoot();
			if (patchArrange() || tries > 80) clearInterval(timer);
		}, 50);
	}

	// The desktop bundle renders in the same turn it loads. Patching arrange_layout
	// on a timer can lose that race, so correct a tile that still says Exhibits.
	function miceIconUrl() {
		var style = "subtle";
		if (window.frappe && frappe.boot && frappe.boot.desktop_icon_style) {
			style = String(frappe.boot.desktop_icon_style).toLowerCase();
		}
		var path = "assets/logistics/icons/desktop_icons/" + style + "/mice.svg";
		var urls =
			window.frappe &&
			frappe.boot &&
			frappe.boot.desktop_icon_urls &&
			frappe.boot.desktop_icon_urls.logistics &&
			frappe.boot.desktop_icon_urls.logistics[style];
		if (!urls || urls.indexOf(path) !== -1) return "/" + path;
		return "";
	}

	function rewriteTile(tile) {
		var title = tile.querySelector(".icon-title");
		var caption = title ? title.textContent.trim() : "";
		if (tile.getAttribute("data-id") !== EXHIBITS && caption !== EXHIBITS) return;
		if (title) title.textContent = MICE;
		var url = miceIconUrl();
		if (!url) return;
		var container = tile.querySelector(".icon-container");
		if (!container) return;
		var img = container.querySelector("img.app-icon");
		if (!img) {
			container.innerHTML = '<img class="app-icon" src="' + url + '" alt="MICE">';
			return;
		}
		if (img.getAttribute("src") && img.getAttribute("src").indexOf("/mice.svg") === -1) {
			img.setAttribute("src", url);
			img.setAttribute("alt", MICE);
		}
	}

	function watchTiles() {
		if (!window.MutationObserver || !document.body) return;
		var rewrite = function () {
			document.querySelectorAll("a.desktop-icon").forEach(rewriteTile);
		};
		rewrite();
		var observer = new MutationObserver(rewrite);
		observer.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", function () {
			watch();
			watchTiles();
		});
	} else {
		watch();
		watchTiles();
	}
})();
