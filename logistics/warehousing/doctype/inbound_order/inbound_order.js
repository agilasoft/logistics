// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inbound Order", {
  refresh(frm) {
    // Show button only for submitted Inbound Orders
    if (!frm.is_new() && frm.doc.docstatus === 1) {
      frm.add_custom_button(
        __("Warehouse Job"),
        () => {
          frappe.model.open_mapped_doc({
            method: "logistics.warehousing.doctype.inbound_order.inbound_order.make_warehouse_job",
            frm: frm
          });
        },
        __("Create") // goes under the Create menu
      );
    }
  }
});

// Client Script for DocType: Inbound Order
frappe.ui.form.on("Inbound Order", {
  refresh(frm) {
    if (!frm.is_new() && [0].includes(frm.doc.docstatus)) {
      frm.add_custom_button(__("Handling Unit"), () => {
        const grid = frm.fields_dict.items?.grid;
        const selected = grid?.get_selected_children() || [];
        if (!selected.length) {
          frappe.msgprint(__("Please select one or more rows in Items first."));
          return;
        }

        const d = new frappe.ui.Dialog({
          title: __("Allocate Handling Unit to Selected Items"),
          fields: [
            {
              fieldname: "hu_type",
              label: __("Handling Unit Type"),
              fieldtype: "Link",
              options: "Handling Unit Type",
              reqd: 1,
              onchange: () => {
                d.fields_dict.handling_unit.get_query = () => {
                  const hut = d.get_value("hu_type");
                  return hut ? { filters: { type: hut } } : {};
                };
                d.set_value("handling_unit", null);
              }
            },
            {
              fieldname: "handling_unit",
              label: __("Handling Unit"),
              fieldtype: "Link",
              options: "Handling Unit",
              reqd: 1,
              get_query: () => {
                const hut = d.get_value("hu_type");
                return hut ? { filters: { type: hut } } : {};
              }
            }
          ],
          primary_action_label: __("Allocate"),
          primary_action(values) {
            d.hide();
            const rownames = selected.map(r => r.name);

            frappe.call({
              method: "logistics.warehousing.doctype.inbound_order.inbound_order.allocate_existing_handling_unit",
              args: {
                source_name: frm.doc.name,
                handling_unit_type: values.hu_type,
                handling_unit: values.handling_unit,
                item_row_names: rownames
              },
              freeze: true,
              freeze_message: __("Allocating..."),
              callback(r) {
                const count = (r && r.message && r.message.updated_count) || 0;
                frappe.msgprint(__("{0} row(s) allocated to Handling Unit <b>{1}</b>.", [count, values.handling_unit]));

                // Update the selected child rows in memory
                selected.forEach(ch => {
                  ch.handling_unit = values.handling_unit;
                  ch.handling_unit_type = values.hu_type;   // <<< add this
                });
                frm.refresh_field("items");
              }
            });
          }
        });

        d.show();
      }, __("Allocate"));
    }
  }
});

