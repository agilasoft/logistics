frappe.ready(function() {
	// Add "Return to List" button
	var returnButton = $('<button type="button" class="btn btn-secondary btn-sm" style="margin-left: 10px;">Return to List</button>');
	
	// Add click handler
	returnButton.click(function() {
		window.location.href = '/inbound-orders';
	});
	
	// Insert the button after the page title
	$('.page-title').after(returnButton);
	
	// Optional: Hide breadcrumb navigation
	$('.breadcrumb').hide();
})