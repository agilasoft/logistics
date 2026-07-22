// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Cross-Docking Order', {
  document_list_template: function (frm) {
    if (!frm.doc.name || frm.doc.__islocal) return;
    frm.save().then(function () {
      frappe.call({
        method: "logistics.document_management.api.populate_documents_from_template",
        args: { doctype: frm.doctype, docname: frm.doc.name },
        callback: function (r) {
          if (r.message) {
            frm.reload_doc();
            if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
          }
        }
      });
    });
  },
  refresh(frm) {
    if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
      logistics.apply_one_off_sales_quote_order_standard(frm);
    }
    frm.set_query("sales_quote", function () {
      return {
        query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
        filters: {
          service_type: "Cross-Docking",
          reference_doctype: "Cross-Docking Order",
          reference_name: frm.doc.name || "",
        },
      };
    });
    if (window.logistics_load_documents_html) {
      window.logistics_load_documents_html(frm, "Cross-Docking Order");
    }
    if (frm.layout && frm.layout.wrapper) {
      frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
        if (window.logistics_load_documents_html) {
          window.logistics_load_documents_html(frm, "Cross-Docking Order");
        }
      });
    }

    if (!frm.is_new() && !frm.doc.__islocal && frm.fields_dict.documents) {
      frm.add_custom_button(__('Get Documents'), function() {
        frappe.call({
          method: 'logistics.document_management.api.populate_documents_from_template',
          args: { doctype: 'Cross-Docking Order', docname: frm.doc.name },
          callback: function(r) {
            if (r.message && r.message.added !== undefined) {
              frm.reload_doc();
              frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
            }
          }
        });
      }, __('Action'));
    }

    if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
      frm.add_custom_button(
        __('Warehouse Job'),
        function () {
          frappe.model.open_mapped_doc({
            method: "logistics.warehousing.doctype.cross_docking_order.cross_docking_order.make_warehouse_job",
            frm: frm
          });
        },
        __('Create')
      );
    }

    if (frm.doc.contract && frm.doc.docstatus === 0) {
      frm.add_custom_button(__("Get Charges from Contract"), function () {
        const meaningful = (frm.doc.charges || []).some((r) =>
          r.item_code || r.charge_item || r.item || r.item_charge
        );
        if (meaningful) {
          frappe.confirm(
            __("Replace all charge lines with cross-dock charges from this contract?"),
            () => populate_cross_docking_order_charges_from_contract(frm, true)
          );
        } else {
          populate_cross_docking_order_charges_from_contract(frm, true);
        }
      }, __("Action"));
    }


    if (frm.fields_dict.docks) {
      frm.set_query("dock_door", "docks", function(doc, cdt, cdn) {
        const row = locals[cdt][cdn] || {};
        const filters = [];
        if (row.direction === "Outbound") {
          filters.push(["Dock Door", "outbound", "=", 1]);
        } else {
          filters.push(["Dock Door", "inbound", "=", 1]);
        }
        return { filters };
      });
    }
  },

  onload(frm) {
    maybe_set_planned_date(frm);
    if (frm.doc.contract && !(frm.doc.charges || []).length) {
      populate_cross_docking_order_charges_from_contract(frm, false);
    }
  },

  before_save(frm) {
    if (!frm.doc.planned_date) maybe_set_planned_date(frm, true);
  },

  charges_add(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },

  validate(frm) {
    (frm.doc.charges || []).forEach(row => {
      const qty  = parseFloat(row.quantity) || 0;
      const rate = parseFloat(row.unit_rate) || 0;
      row.total = qty * rate;
    });
    frm.refresh_field("charges");
  },

  contract(frm) {
    if (frm.doc.contract) {
      frappe.db.get_value("Warehouse Contract", frm.doc.contract, ["shipper", "consignee"], function(r) {
        if (r) {
          if (r.shipper) frm.set_value("shipper", r.shipper);
          if (r.consignee) frm.set_value("consignee", r.consignee);
        }
      });
      populate_cross_docking_order_charges_from_contract(frm, false);
    } else {
      frm.set_value("shipper", "");
      frm.set_value("consignee", "");
    }
  }
});

function _resolve_item(row) {
  return row.charge_item || row.item_code || row.item || row.item_charge;
}

function _apply_vals(cdt, cdn, m) {
  if (!m) return;
  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "unit_rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);
  if (m.uom) {
    frappe.model.set_value(cdt, cdn, "uom", m.uom);
  } else {
    const row = locals[cdt][cdn];
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
          }
        }
      });
    }
  }
}

function _fetch(frm, cdt, cdn, context) {
  const row = locals[cdt][cdn];
  const contract = frm.doc.contract;
  const item_code = _resolve_item(row);
  if (!contract || !item_code) return;

  frappe.call({
    method: "logistics.warehousing.api.get_contract_charge",
    args: { contract, item_code, context },
  }).then(r => _apply_vals(cdt, cdn, r.message));
}

function populate_cross_docking_order_charges_from_contract(frm, replace) {
  if (!frm.doc.contract) return;
  if (!replace && (frm.doc.charges || []).length) return;

  frappe.call({
    method: "logistics.warehousing.doctype.warehouse_job.warehouse_job.get_contract_charge_items",
    args: { warehouse_contract: frm.doc.contract, context: "cross_dock" },
    callback: function (r) {
      const msg = r.message || {};
      if (!msg.ok) {
        frappe.msgprint({
          title: __("Contract charges"),
          message: msg.message || __("Could not load charges from the contract."),
          indicator: "red",
        });
        return;
      }
      const items = msg.items || [];
      if (!items.length) {
        frappe.show_alert({
          message: __("No cross-dock charges are set on this Warehouse Contract."),
          indicator: "orange",
        });
        return;
      }
      if (replace) {
        frm.clear_table("charges");
      }
      const cdt = "Cross-Docking Order Charges";
      items.forEach(function (ci) {
        if (!ci.item_charge) return;
        const row = frappe.model.add_child(frm.doc, "charges");
        const cdn = row.name;
        frappe.model.set_value(cdt, cdn, "item_code", ci.item_charge);
        if (ci.item_name) frappe.model.set_value(cdt, cdn, "item_name", ci.item_name);
        if (typeof ci.rate === "number") frappe.model.set_value(cdt, cdn, "unit_rate", ci.rate);
        if (ci.currency) frappe.model.set_value(cdt, cdn, "currency", ci.currency);
        if (ci.uom) frappe.model.set_value(cdt, cdn, "uom", ci.uom);
        frappe.model.set_value(cdt, cdn, "quantity", 1);
        recalc_charge_total(cdt, cdn);
      });
      frm.refresh_field("charges");
      frappe.show_alert(
        { message: __("Added {0} charge line(s) from contract.", [items.length]), indicator: "green" },
        4
      );
    },
  });
}

frappe.ui.form.on("Cross-Docking Order Charges", {
  charge_item(frm, cdt, cdn) { _fetch(frm, cdt, cdn, "cross_dock"); },
  item_code(frm, cdt, cdn)  { _fetch(frm, cdt, cdn, "cross_dock"); },
  quantity(frm, cdt, cdn)   { recalc_charge_total(cdt, cdn); },
  unit_rate(frm, cdt, cdn)  { recalc_charge_total(cdt, cdn); },
});

frappe.ui.form.on("Cross-Docking Order Dock", {
  direction(frm, cdt, cdn) {
    if (locals[cdt][cdn].dock_door) {
      frappe.model.set_value(cdt, cdn, "dock_door", "");
    }
  }
});

function maybe_set_planned_date(frm, force = false) {
  if (!force && (frm.doc.planned_date || frm.__planned_date_set)) return;

  frappe.db.get_value("Warehouse Settings", frappe.defaults.get_user_default("Company"), "planned_date_offset_days")
    .then((val) => {
      const offset = parseInt(val, 10) || 0;
      const nowStr = frappe.datetime.now_datetime();
      const planned = addDaysPreserveTime(nowStr, offset);
      frm.set_value("planned_date", planned);
      frm.__planned_date_set = true;
    })
    .catch(() => {
      frm.set_value("planned_date", frappe.datetime.now_datetime());
      frm.__planned_date_set = true;
    });
}

function addDaysPreserveTime(baseStr, days) {
  if (window.dayjs) {
    return window.dayjs(baseStr).add(days, "day").format("YYYY-MM-DD HH:mm:ss");
  } else if (window.moment) {
    return window.moment(baseStr, "YYYY-MM-DD HH:mm:ss").add(days, "days").format("YYYY-MM-DD HH:mm:ss");
  } else {
    const d = new Date(baseStr.replace(" ", "T"));
    d.setDate(d.getDate() + days);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
}

function recalc_charge_total(cdt, cdn) {
  const row  = locals[cdt][cdn];
  const qty  = parseFloat(row.quantity) || 0;
  const rate = parseFloat(row.unit_rate) || 0;
  frappe.model.set_value(cdt, cdn, "total", qty * rate);
}

frappe.ui.form.on("Cross-Docking Order Item", {
  serial_tracking(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
    }
    frm.fields_dict.items.grid.refresh();
  },

  quantity(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking && row.quantity != 1) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
      frappe.show_alert(__("Serial-tracked items must have Quantity = 1"));
    }
  },

  item(frm, cdt, cdn) {
    _fetch(frm, cdt, cdn, "cross_dock");
  },

});


