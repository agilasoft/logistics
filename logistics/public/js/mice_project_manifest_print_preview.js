// Desk print preview shell is portrait (8.3in). Widen it to A4 landscape
// only while MICE Project Manifest is the selected format.
const MICE_PROJECT_MANIFEST = "MICE Project Manifest";

function apply_mice_manifest_preview_width(view) {
	if (!view || !view.print_wrapper) {
		return;
	}
	const $preview = view.print_wrapper.find(".print-preview");
	if (!$preview.length) {
		return;
	}
	const format = view.selected_format ? view.selected_format() : "";
	if (format === MICE_PROJECT_MANIFEST) {
		$preview.css({
			width: "11.69in",
			maxWidth: "11.69in",
			minHeight: "8.27in",
			boxSizing: "border-box",
		});
	} else {
		$preview.css({
			width: "",
			maxWidth: "",
			minHeight: "",
			boxSizing: "",
		});
	}
}

function patch_mice_manifest_print_view() {
	const PrintView = frappe.ui && frappe.ui.form && frappe.ui.form.PrintView;
	if (!PrintView) {
		return false;
	}
	if (PrintView.prototype._mice_manifest_preview_patched) {
		return true;
	}
	const original = PrintView.prototype.setup_print_format_dom;
	PrintView.prototype.setup_print_format_dom = function (out, $print_format) {
		const result = original.apply(this, arguments);
		apply_mice_manifest_preview_width(this);
		return result;
	};
	PrintView.prototype._mice_manifest_preview_patched = true;
	return true;
}

function apply_mice_manifest_preview_width_from_dom() {
	const $preview = $(".print-preview-wrapper .print-preview");
	if (!$preview.length) {
		return;
	}
	const format = $(
		".print-preview-sidebar [data-fieldname='print_format'] input"
	).val();
	if (format === MICE_PROJECT_MANIFEST) {
		$preview.css({
			width: "11.69in",
			maxWidth: "11.69in",
			minHeight: "8.27in",
			boxSizing: "border-box",
		});
	} else if (format) {
		$preview.css({
			width: "",
			maxWidth: "",
			minHeight: "",
			boxSizing: "",
		});
	}
}

function watch_mice_manifest_print_preview() {
	const route = frappe.get_route ? frappe.get_route() : [];
	if (!route || route[0] !== "print") {
		return;
	}
	let tries = 0;
	const timer = setInterval(() => {
		tries += 1;
		const patched = patch_mice_manifest_print_view();
		if (patched) {
			apply_mice_manifest_preview_width_from_dom();
		}
		if (patched || tries > 50) {
			clearInterval(timer);
		}
	}, 100);
}

function bind_mice_manifest_print_preview() {
	if (typeof frappe === "undefined" || !frappe.router || !frappe.router.on) {
		setTimeout(bind_mice_manifest_print_preview, 50);
		return;
	}
	frappe.router.on("change", watch_mice_manifest_print_preview);
	watch_mice_manifest_print_preview();
}

bind_mice_manifest_print_preview();
