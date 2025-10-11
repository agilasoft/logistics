frappe.ui.form.on('Warehouse Contract Item', {
    refresh: function(frm) {
        update_billing_method_options(frm);
    },
    
    storage_charge: function(frm) {
        update_billing_method_options(frm);
    },
    
    inbound_charge: function(frm) {
        update_billing_method_options(frm);
    },
    
    outbound_charge: function(frm) {
        update_billing_method_options(frm);
    },
    
    transfer_charge: function(frm) {
        update_billing_method_options(frm);
    },
    
    vas_charge: function(frm) {
        update_billing_method_options(frm);
    },
    
    stocktake_charge: function(frm) {
        update_billing_method_options(frm);
    }
});

function update_billing_method_options(frm) {
    console.log("Updating billing method options");
    
    // Get the current charge types
    const storage_charge = frm.doc.storage_charge;
    const inbound_charge = frm.doc.inbound_charge;
    const outbound_charge = frm.doc.outbound_charge;
    const transfer_charge = frm.doc.transfer_charge;
    const vas_charge = frm.doc.vas_charge;
    const stocktake_charge = frm.doc.stocktake_charge;
    
    // Determine which charge types are active
    const active_charges = [];
    if (storage_charge) active_charges.push('storage');
    if (inbound_charge) active_charges.push('inbound');
    if (outbound_charge) active_charges.push('outbound');
    if (transfer_charge) active_charges.push('transfer');
    if (vas_charge) active_charges.push('vas');
    if (stocktake_charge) active_charges.push('stocktake');
    
    console.log("Active charges:", active_charges);
    
    // Define billing method options for each charge type
    const billing_options = {
        storage: ['Per Volume', 'Per Weight', 'Per Handling Unit', 'High Water Mark'],
        inbound: ['Per Volume', 'Per Piece', 'Per Weight', 'Per Container'],
        outbound: ['Per Volume', 'Per Piece', 'Per Weight', 'Per Container'],
        transfer: ['Per Volume', 'Per Piece', 'Per Weight'],
        vas: ['Per Volume', 'Per Piece', 'Per Hour'],
        stocktake: ['Per Volume', 'Per Piece']
    };
    
    // Get all unique options from active charges
    let all_options = [];
    active_charges.forEach(charge_type => {
        if (billing_options[charge_type]) {
            all_options = all_options.concat(billing_options[charge_type]);
        }
    });
    
    // Remove duplicates and sort
    const unique_options = [...new Set(all_options)].sort();
    
    console.log("Available billing options:", unique_options);
    
    // Update the billing method field options
    if (frm.fields_dict.billing_method) {
        frm.fields_dict.billing_method.df.options = unique_options.join('\n');
        frm.fields_dict.billing_method.refresh();
        
        // If current value is not in new options, reset to first option
        if (frm.doc.billing_method && !unique_options.includes(frm.doc.billing_method)) {
            frm.set_value('billing_method', unique_options[0] || '');
        }
    }
}