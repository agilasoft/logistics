// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Periodic Billing', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__('Get Charges'), async () => {
        try {
          const r = await frappe.call({
            method: 'logistics.warehousing.api.periodic_billing_get_charges',
            args: { periodic_billing: frm.doc.name, clear_existing: 1 },
            freeze: true,
            freeze_message: __('Fetching charges...'),
          });

          let msg = '';
          if (r && r.message) {
            if (typeof r.message === 'string') {
              msg = r.message;
            } else if (typeof r.message.message === 'string') {
              msg = r.message.message;
            } else {
              msg = __('Charges fetched.');
            }
          } else {
            msg = __('Charges fetched.');
          }

          frappe.msgprint({ title: __('Get Charges'), message: msg, indicator: 'green' });
          frm.reload_doc();
        } catch (e) {
          const server = (e && e.message) ? e.message : (e && e._server_messages) ? e._server_messages : e;
          frappe.msgprint({ title: __('Error'), indicator: 'red', message: String(server || __('Unknown error')) });
        }
      }, __('Action'));
    }
  }
});


frappe.ui.form.on('Periodic Billing', {
  refresh(frm) {
    if (frm.is_new()) return;

    // Create → Sales Invoice
    frm.add_custom_button(__('Sales Invoice'), () => {
      frappe.call({
        method: 'logistics.warehousing.api.create_sales_invoice_from_periodic_billing',
        args: {
          periodic_billing: frm.doc.name,
          posting_date: frm.doc.date || undefined
          // you can also pass company / cost_center here if you have those fields on PB:
          // company: frm.doc.company,
          // cost_center: frm.doc.cost_center,
        },
        freeze: true,
        freeze_message: __('Creating Sales Invoice…'),
      }).then(r => {
        const si = r?.message?.sales_invoice;
        if (si) {
          frappe.show_alert({ message: __('Sales Invoice {0} created', [si]), indicator: 'green' });
          frappe.set_route('Form', 'Sales Invoice', si);
        } else {
          frappe.msgprint(__('No Sales Invoice returned.'));
        }
      }).catch(e => {
        frappe.msgprint(__('Failed to create Sales Invoice.'));
        // Optional: console.error(e);
      });
    }, __('Create'));
  },
});
