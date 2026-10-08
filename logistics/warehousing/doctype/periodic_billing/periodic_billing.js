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

    // Customer invoice, and optional internal billing or intercompany, in one window.
    if (frm.doc.docstatus !== 2) {
      frm.add_custom_button(__('Create Billing'), () => {
        open_periodic_billing_dialog(frm);
      }, __('Action'));
    }
  },
});

function periodic_billing_charge_table(charges) {
  var header = [
    '<table class="table table-bordered table-sm">',
    '<thead><tr>',
    '<th style="width:32px"><input type="checkbox" id="pb_billing_select_all" checked /></th>',
    '<th>' + __('Item') + '</th>',
    '<th>' + __('Warehouse Job') + '</th>',
    '<th class="text-right">' + __('Qty') + '</th>',
    '<th class="text-right">' + __('Amount') + '</th>',
    '</tr></thead><tbody>'
  ].join('');
  var rows = (charges || []).map(function (charge) {
    var posting = '';
    if (charge.posting === 'internal') {
      posting = '<div class="text-muted">' + __('Internal') + '</div>';
    } else if (charge.posting === 'intercompany') {
      posting = '<div class="text-muted">' + __('Intercompany') + '</div>';
    }
    return [
      '<tr>',
      '<td><input type="checkbox" class="pb-billing-cb" data-idx="' + charge.idx + '" checked /></td>',
      '<td>' + frappe.utils.escape_html(charge.item_name || charge.item_code || '') + posting + '</td>',
      '<td>' + frappe.utils.escape_html(charge.warehouse_job || '') + '</td>',
      '<td class="text-right">' + (charge.quantity != null ? charge.quantity : '') + '</td>',
      '<td class="text-right">' + frappe.format(charge.amount || 0, { fieldtype: 'Currency' }) + '</td>',
      '</tr>'
    ].join('');
  });
  return header + rows.join('') + '</tbody></table>';
}

function periodic_billing_doc_link(doctype, name) {
  if (!name) {
    return '';
  }
  var label = frappe.utils.escape_html(name);
  if (typeof frappe.utils.get_form_link === 'function') {
    return frappe.utils.get_form_link(doctype, name, true, label);
  }
  return label;
}

function open_periodic_billing_dialog(frm) {
  if (window.logistics && logistics.menu && !logistics.menu.can('Sales Invoice', 'create')) {
    frappe.msgprint({
      title: __('Not Permitted'),
      message: __('You do not have permission to create a Sales Invoice.'),
      indicator: 'red',
    });
    return;
  }
  frappe.call({
    method: 'logistics.warehousing.periodic_billing_posting.get_periodic_billing_posting_options',
    args: { periodic_billing: frm.doc.name },
    freeze: true,
    freeze_message: __('Loading charges...'),
  }).then(function (r) {
    var data = r.message || {};
    if (!data.charges || !data.charges.length) {
      frappe.msgprint({
        title: __('Create Billing'),
        message: __('No charges to bill. Use Get Charges first.'),
        indicator: 'orange',
      });
      return;
    }
    var fields = [
      { fieldname: 'posting_date', fieldtype: 'Date', label: __('Invoice Date'), default: data.default_posting_date, reqd: 1 },
      { fieldname: 'customer', fieldtype: 'Link', label: __('Customer'), options: 'Customer', default: data.customer, reqd: 1 },
      { fieldname: 'charges_section', fieldtype: 'Section Break', label: __('Charges to Include') },
      { fieldname: 'charges_html', fieldtype: 'HTML', options: periodic_billing_charge_table(data.charges) },
      { fieldname: 'posting_section', fieldtype: 'Section Break', label: __('Also post') },
    ];
    if (data.show_internal_billing) {
      fields.push({
        fieldname: 'internal_billing',
        fieldtype: 'Check',
        label: __('Internal Billing'),
        description: __('Journal entry for linked warehouse jobs in the same company as the main job. Uses the selected charge amounts.'),
      });
    }
    if (data.show_intercompany) {
      fields.push({
        fieldname: 'intercompany',
        fieldtype: 'Check',
        label: __('Intercompany Transactions'),
        description: __('Sales invoice and purchase invoice for linked warehouse jobs in another company. Uses the selected charge amounts.'),
      });
    }
    if (data.intercompany_disabled) {
      fields.push({
        fieldname: 'intercompany_note',
        fieldtype: 'HTML',
        options: '<p class="text-muted">' + __('Intercompany invoicing is turned off in Intercompany Settings.') + '</p>',
      });
    }
    if (!data.show_internal_billing && !data.show_intercompany && !data.intercompany_disabled) {
      fields.push({
        fieldname: 'posting_note',
        fieldtype: 'HTML',
        options: '<p class="text-muted">' + __('Internal billing and intercompany transactions appear when a charge is linked to a warehouse job in the same company or another company.') + '</p>',
      });
    }

    var dialog = new frappe.ui.Dialog({
      title: __('Create Billing'),
      size: 'large',
      fields: fields,
      primary_action_label: __('Create Billing'),
      primary_action: function (values) {
        var idxs = [];
        dialog.$wrapper.find('input.pb-billing-cb:checked').each(function () {
          idxs.push(parseInt($(this).attr('data-idx'), 10));
        });
        if (!idxs.length) {
          frappe.msgprint({
            title: __('Select Charges'),
            message: __('Select at least one charge to include.'),
            indicator: 'orange',
          });
          return;
        }
        dialog.hide();
        frappe.call({
          method: 'logistics.warehousing.periodic_billing_posting.create_billing',
          args: {
            periodic_billing: frm.doc.name,
            posting_date: values.posting_date,
            customer: values.customer,
            selected_charge_idxs: JSON.stringify(idxs),
            internal_billing: values.internal_billing ? 1 : 0,
            intercompany: values.intercompany ? 1 : 0,
          },
          freeze: true,
          freeze_message: __('Creating billing...'),
        }).then(function (create_r) {
          show_periodic_billing_result(create_r.message || {});
          frm.reload_doc();
        });
      },
    });
    dialog.show();
    dialog.$wrapper.find('#pb_billing_select_all').on('change', function () {
      dialog.$wrapper.find('input.pb-billing-cb').prop('checked', $(this).prop('checked'));
    });
  });
}

function show_periodic_billing_result(message) {
  var parts = [];
  if (message.sales_invoice) {
    parts.push('<p>' + __('Customer Sales Invoice') + ': ' + periodic_billing_doc_link('Sales Invoice', message.sales_invoice) + '</p>');
  }
  (message.journal_entries || []).forEach(function (row) {
    parts.push('<p>' + __('Internal Billing') + ' ' + frappe.utils.escape_html(row.job || '') + ': ' + periodic_billing_doc_link('Journal Entry', row.journal_entry) + '</p>');
  });
  (message.intercompany || []).forEach(function (row) {
    parts.push(
      '<p>' + __('Intercompany') + ' ' + frappe.utils.escape_html(row.job || '') + ': ' +
      periodic_billing_doc_link('Sales Invoice', row.sales_invoice) + ' / ' +
      periodic_billing_doc_link('Purchase Invoice', row.purchase_invoice) + '</p>'
    );
  });
  if ((message.errors || []).length) {
    parts.push('<p><strong>' + __('Errors') + '</strong></p><ul>');
    message.errors.forEach(function (err) {
      parts.push('<li>' + frappe.utils.escape_html(err) + '</li>');
    });
    parts.push('</ul>');
  }
  var indicator = 'green';
  if ((message.errors || []).length && (message.journal_entries || []).length + (message.intercompany || []).length) {
    indicator = 'orange';
  } else if ((message.errors || []).length) {
    indicator = 'orange';
  }
  frappe.msgprint({
    title: __('Create Billing'),
    message: parts.join('') || message.message || __('Billing created.'),
    indicator: indicator,
  });
}
