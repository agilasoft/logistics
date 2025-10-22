// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Inbound Order Item', {
    refresh: function(frm) {
        update_uom_fields(frm);
    }
});

function update_uom_fields(frm) {
    console.log("Auto-populating UOM fields from Warehouse Settings");
    console.log("Form fields available:", Object.keys(frm.fields_dict));
    
    // Get UOM values from Warehouse Settings
    const company = frappe.defaults.get_user_default("Company");
    console.log("Company:", company);
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Warehouse Settings",
            name: company,
            fieldname: ["default_volume_uom", "default_weight_uom"]
        },
        callback: function(r) {
            console.log("UOM response:", r);
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                console.log("Volume UOM:", volume_uom, "Weight UOM:", weight_uom);
                
                // Check if fields exist
                console.log("volume_uom field exists:", !!frm.fields_dict.volume_uom);
                console.log("weight_uom field exists:", !!frm.fields_dict.weight_uom);
                
                // Auto-populate volume UOM field
                if (frm.fields_dict.volume_uom && volume_uom) {
                    frm.set_value("volume_uom", volume_uom);
                    console.log("Set volume_uom to:", volume_uom);
                } else {
                    console.log("Cannot set volume_uom - field missing or no value");
                }
                
                // Auto-populate weight UOM field
                if (frm.fields_dict.weight_uom && weight_uom) {
                    frm.set_value("weight_uom", weight_uom);
                    console.log("Set weight_uom to:", weight_uom);
                } else {
                    console.log("Cannot set weight_uom - field missing or no value");
                }
            } else {
                console.log("No UOM message received");
            }
        }
    });
}

function fetch_uom_from_contract(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const item = row.item;
    
    // Access the parent form to get the contract
    const parent_frm = frm.frm;
    if (!parent_frm) {
        console.log("Parent form not found");
        return;
    }
    
    const contract = parent_frm.doc.contract;
    
    // Check if we have both item and contract
    if (!item || !contract) {
        console.log("Missing item or contract for UOM fetch. Item:", item, "Contract:", contract);
        return;
    }
    
    console.log("Fetching UOM from contract for item:", item, "contract:", contract);
    
    frappe.call({
        method: "logistics.warehousing.api.get_contract_charge",
        args: {
            contract: contract,
            item_code: item,
            context: "inbound"
        },
        callback: function(r) {
            console.log("Contract charge response:", r);
            if (r.message && r.message.uom) {
                frappe.model.set_value(cdt, cdn, "uom", r.message.uom);
                console.log("Set UOM from contract to:", r.message.uom);
            } else {
                console.log("No UOM found in contract for this item");
                // Fallback to item's default UOM if no contract UOM found
                if (row.item) {
                    frappe.call({
                        method: "frappe.client.get_value",
                        args: {
                            doctype: "Warehouse Item",
                            name: row.item,
                            fieldname: ["uom"]
                        },
                        callback: function(item_r) {
                            if (item_r.message && item_r.message.uom) {
                                frappe.model.set_value(cdt, cdn, "uom", item_r.message.uom);
                                console.log("Set UOM from item default to:", item_r.message.uom);
                            }
                        }
                    });
                }
            }
        }
    });
}