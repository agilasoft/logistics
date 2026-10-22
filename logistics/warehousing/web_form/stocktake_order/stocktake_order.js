function bind_company_dimension_queries() {
	var web_form = frappe.web_form;
	if (!web_form || !web_form.fields_dict) return;
	var company = function () {
		return web_form.get_value("company") || "";
	};
	if (web_form.fields_dict.branch) {
		web_form.fields_dict.branch.get_query = function () {
			var value = company();
			return value ? { filters: { custom_company: value } } : {};
		};
	}
	if (web_form.fields_dict.cost_center) {
		web_form.fields_dict.cost_center.get_query = function () {
			var filters = { is_group: 0, disabled: 0 };
			var value = company();
			if (value) filters.company = value;
			return { filters: filters };
		};
	}
}

frappe.ready(function() {
	bind_company_dimension_queries();

	// Add "Return to List" button
	var returnButton = $('<button type="button" class="btn btn-secondary btn-sm" style="margin-left: 10px;">Return to List</button>');
	
	// Add click handler
	returnButton.click(function() {
		window.location.href = '/stocktake-orders';
	});
	
	// Insert the button after the page title
	$('.page-title').after(returnButton);
	
	// Optional: Hide breadcrumb navigation
	$('.breadcrumb').hide();
})
