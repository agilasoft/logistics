// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Periodic Billing', {
  refresh(frm) {
    if (frm.is_new()) return;

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
        console.log('Response message:', r.message);
        console.log('Response type:', typeof r.message);

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

        console.log('Final message:', msg);
        frappe.msgprint({ title: __('Get Charges'), message: msg, indicator: 'green' });
        
        // Check if charges were actually created
        if (r && r.message && r.message.created) {
          console.log('Charges created:', r.message.created);
          console.log('Grand total:', r.message.grand_total);
        }
        
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
          console.log('Loading contract setup summary for:', frm.doc.warehouse_contract);
          const summary = await frappe.call({
            method: 'logistics.warehousing.billing.get_contract_setup_summary',
            args: { warehouse_contract: frm.doc.warehouse_contract },
            freeze: true,
            freeze_message: __('Loading contract setup...'),
          });

          console.log('Contract setup summary response:', summary);
          
          if (summary && summary.message) {
            const s = summary.message;
            
            // Check if the response contains an error
            if (s.error) {
              frappe.msgprint({ 
                title: __('Error'), 
                indicator: 'red', 
                message: __('Error loading contract setup: ') + s.error
              });
              return;
            }
            
            // Validate that we have the required data
            if (!s.contract_name) {
              frappe.msgprint({ 
                title: __('Error'), 
                indicator: 'red', 
                message: __('No contract data found. Please check if the contract exists and is valid.') 
              });
              return;
            }
            
            let msg = `<h4>Contract Setup Summary</h4>
              <p><strong>Contract:</strong> ${s.contract_name || 'N/A'}</p>
              <p><strong>Customer:</strong> ${s.customer || 'N/A'}</p>
              <p><strong>Valid Until:</strong> ${s.valid_until || 'Not specified'}</p>
              <p><strong>Total Contract Items:</strong> ${s.total_items || 0}</p>
              <hr>
              <h5>Charge Types:</h5>
              <ul>
                <li>Storage Charges: ${s.storage_charges || 0}</li>
                <li>Inbound Charges: ${s.inbound_charges || 0}</li>
                <li>Outbound Charges: ${s.outbound_charges || 0}</li>
                <li>Transfer Charges: ${s.transfer_charges || 0}</li>
                <li>VAS Charges: ${s.vas_charges || 0}</li>
                <li>Stocktake Charges: ${s.stocktake_charges || 0}</li>
              </ul>`;
            
            frappe.msgprint({ 
              title: __('Contract Setup Summary'), 
              message: msg, 
              indicator: 'blue' 
            });
          } else {
            frappe.msgprint({ 
              title: __('Error'), 
              indicator: 'red', 
              message: __('No data returned from contract setup summary') 
            });
          }
        } catch (e) {
          console.error('Error loading contract setup summary:', e);
          frappe.msgprint({ 
            title: __('Error'), 
            indicator: 'red', 
            message: __('Failed to load contract setup summary: ') + (e.message || String(e))
          });
        }
      }, __('Action'));
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
    }, __('Action'));
  },
});
