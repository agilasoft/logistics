// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Air Freight Job", {
	refresh(frm) {
		console.log("Air Freight Job form refreshed");
		console.log("Origin Port:", frm.doc.origin_port);
		console.log("Destination Port:", frm.doc.destination_port);
		
		// Only call if not already called recently
		if (!frm._milestone_html_called) {
			frm._milestone_html_called = true;
			console.log("Calling get_milestone_html...");
			frm.call('get_milestone_html').then(r => {
				console.log("Response from get_milestone_html:", r);
				console.log("Message content:", r.message);
				if (r.message) {
					const html = r.message || '';
					
					// Get the HTML field wrapper and set content directly
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(html);
						console.log("HTML set directly in DOM (virtual field)");
					}
					
					// Don't set the field value since it's virtual - just update DOM
					console.log("Milestone HTML rendered successfully");
				} else {
					console.log("No message in response");
				}
			}).catch(err => {
				console.error("Error calling get_milestone_html:", err);
			});
			
			// Reset flag after 2 seconds
			setTimeout(() => {
				frm._milestone_html_called = false;
			}, 2000);
		}
	},
	
	origin_port(frm) {
		console.log("Origin port changed to:", frm.doc.origin_port);
		// Regenerate milestone HTML when origin port changes
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.call('get_milestone_html').then(r => {
				if (r.message) {
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(r.message);
					}
				}
			});
		}
	},
	
	destination_port(frm) {
		console.log("Destination port changed to:", frm.doc.destination_port);
		// Regenerate milestone HTML when destination port changes
		if (frm.doc.origin_port && frm.doc.destination_port) {
			frm.call('get_milestone_html').then(r => {
				if (r.message) {
					const $wrapper = frm.get_field('milestone_html').$wrapper;
					if ($wrapper) {
						$wrapper.html(r.message);
					}
				}
			});
		}
	}
});
