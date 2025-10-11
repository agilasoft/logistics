frappe.pages['_'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: '_',
		single_column: true
	});
}