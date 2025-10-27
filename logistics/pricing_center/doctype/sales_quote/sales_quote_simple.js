// Simple test JavaScript for Sales Quote
console.log('=== SIMPLE SALES QUOTE JS LOADED ===');

frappe.ui.form.on("Sales Quote", {
    refresh: function(frm) {
        console.log('=== SALES QUOTE REFRESH ===');
        console.log('Document:', frm.doc.name);
        console.log('Transport lines:', frm.doc.transport ? frm.doc.transport.length : 'No transport field');
        
        // Add a simple button to test
        frm.add_custom_button("Test Calculation", function() {
            console.log('=== TEST BUTTON CLICKED ===');
            test_calculation(frm);
        });
        
        // Add button to trigger calculations
        frm.add_custom_button("Calculate Transport", function() {
            console.log('=== CALCULATE TRANSPORT CLICKED ===');
            calculate_all_transport(frm);
        });
    },
    
    on_save: function(frm) {
        console.log('=== SALES QUOTE SAVE ===');
        // Trigger calculations when document is saved
        if (frm.doc.transport && frm.doc.transport.length > 0) {
            console.log('Triggering transport calculations on save');
            calculate_all_transport(frm);
        }
    },
    
    // Test if child table events work
    transport: {
        refresh: function(frm, cdt, cdn) {
            console.log('=== TRANSPORT REFRESH ===', cdt, cdn);
        },
        quantity: function(frm, cdt, cdn) {
            console.log('=== QUANTITY CHANGED ===', cdt, cdn);
            console.log('New value:', locals[cdt][cdn].quantity);
        },
        unit_rate: function(frm, cdt, cdn) {
            console.log('=== UNIT RATE CHANGED ===', cdt, cdn);
            console.log('New value:', locals[cdt][cdn].unit_rate);
        }
    }
});

function test_calculation(frm) {
    console.log('=== TESTING CALCULATION ===');
    
    if (frm.doc.transport && frm.doc.transport.length > 0) {
        console.log('Found transport lines:', frm.doc.transport.length);
        
        // Test the calculation API directly
        frappe.call({
            method: 'logistics.pricing_center.doctype.sales_quote_transport.sales_quote_transport.trigger_calculations_for_line',
            args: {
                line_data: JSON.stringify({
                    item_code: "TEST",
                    calculation_method: "Per Unit",
                    quantity: 10,
                    unit_rate: 100,
                    unit_type: "Weight"
                })
            },
            callback: function(r) {
                console.log('=== CALCULATION RESULT ===');
                console.log('Response:', r);
                if (r.message) {
                    console.log('Success:', r.message.success);
                    console.log('Revenue:', r.message.estimated_revenue);
                    console.log('Cost:', r.message.estimated_cost);
                }
            },
            error: function(err) {
                console.log('=== CALCULATION ERROR ===');
                console.log('Error:', err);
            }
        });
    } else {
        console.log('No transport lines found');
    }
}

function calculate_all_transport(frm) {
    console.log('=== CALCULATING ALL TRANSPORT ===');
    
    if (frm.doc.transport && frm.doc.transport.length > 0) {
        console.log('Found transport lines:', frm.doc.transport.length);
        
        // Save the document to trigger Python validate method
        frm.save().then(function() {
            console.log('=== DOCUMENT SAVED - CALCULATIONS SHOULD BE TRIGGERED ===');
            // Refresh the form to show updated values
            frm.reload_doc();
        });
    } else {
        console.log('No transport lines found');
    }
}
