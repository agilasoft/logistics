// Copyright (c) 2020, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Order', {
	refresh: function(frm) {
		if(frm.doc.docstatus === 1){
			frm.add_custom_button(__('Transport Job'), function(){
				cur_frm.call('create_job','',function(r){});
			}, __("Create"));
		}
	},
});
