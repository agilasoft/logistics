// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Periodic Billing', {
  refresh(frm) {
    if (frm.is_new()) return;

    // Test button
    frm.add_custom_button(__('Test'), async () => {
      console.log('Test button clicked');
      try {
        const r = await frappe.call({
          method: 'logistics.warehousing.api.test_periodic_billing',
          freeze: true,
        });
        console.log('Test response:', r);
        frappe.msgprint({ title: __('Test'), message: r.message.message, indicator: 'green' });
      } catch (e) {
        console.error('Test error:', e);
        frappe.msgprint({ title: __('Error'), indicator: 'red', message: String(e) });
      }
    }, __('Test'));

    // Get Charges button
    frm.add_custom_button(__('Get Charges'), async () => {
      console.log('Get Charges button clicked');
      try {
        console.log('Calling periodic_billing_get_charges with:', frm.doc.name);
        const r = await frappe.call({
          method: 'logistics.warehousing.billing.periodic_billing_get_charges',
          args: { periodic_billing: frm.doc.name, clear_existing: 1 },
          freeze: true,
          freeze_message: __('Fetching charges...'),
        });
        console.log('Response received:', r);

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
    
    // Add contract setup summary button
    if (frm.doc.warehouse_contract) {
      frm.add_custom_button(__('Contract Setup Summary'), async () => {
        try {
          const summary = await frappe.call({
            method: 'logistics.warehousing.billing.get_contract_setup_summary',
            args: { warehouse_contract: frm.doc.warehouse_contract },
            freeze: true,
            freeze_message: __('Loading contract setup...'),
          });

          if (summary && summary.message) {
            const s = summary.message;
            let msg = `<h4>Contract Setup Summary</h4>
              <p><strong>Contract:</strong> ${s.contract_name}</p>
              <p><strong>Customer:</strong> ${s.customer}</p>
              <p><strong>Valid Until:</strong> ${s.valid_until || 'Not specified'}</p>
              <p><strong>Total Contract Items:</strong> ${s.total_items}</p>
              <hr>
              <h5>Charge Types:</h5>
              <ul>
                <li>Storage Charges: ${s.storage_charges}</li>
                <li>Inbound Charges: ${s.inbound_charges}</li>
                <li>Outbound Charges: ${s.outbound_charges}</li>
                <li>Transfer Charges: ${s.transfer_charges}</li>
                <li>VAS Charges: ${s.vas_charges}</li>
                <li>Stocktake Charges: ${s.stocktake_charges}</li>
              </ul>`;
            
            frappe.msgprint({ 
              title: __('Contract Setup Summary'), 
              message: msg, 
              indicator: 'blue' 
            });
          }
        } catch (e) {
          frappe.msgprint({ 
            title: __('Error'), 
            indicator: 'red', 
            message: __('Failed to load contract setup summary') 
          });
        }
      }, __('Info'));
    }

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
