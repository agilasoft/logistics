// Copyright (c) 2025, www.agilasoft.com
// For license information, please see license.txt

(() => {
  const GROUP = __("Action");
  const CREATE_GROUP = __("Create");

  // ---------- Helpers ----------
  const ensureSaved = (frm) => {
    if (!frm.doc.name) {
      frappe.msgprint(__("Please save the document first."));
      return false;
    }
    return true;
  };

  const extractMsg = (res, fallback) => {
    const r = (res && res.message) || res || {};
    if (typeof r === "string") return r;
    return r.message || (typeof fallback === "function" ? fallback(r) : fallback);
  };

  const callServer = async (frm, { method, args, freezing, title, fallback }) => {
    try {
      const r = await frappe.call({ method, args, freeze: true, freeze_message: freezing });
      const msg = extractMsg(r, fallback((r && r.message) || {}));
      frappe.msgprint({ title, message: msg, indicator: "blue" });
      frm.reload_doc();
      return r && r.message;
    } catch (err) {
      console.error(err);
      frappe.msgprint({ title, message: __("See console for details."), indicator: "red" });
      throw err;
    }
  };

  const addBtnIf = (frm, cond, label, handler, group = GROUP) => {
    if (cond) frm.add_custom_button(label, handler, group);
  };

  // ---------- NEW: Item filtering by Customer ----------
  function applyItemCustomerFilter(frm) {
    const cust = frm.doc.customer || null;

    // Orders table (Warehouse Job Order Items)
    if (frm.fields_dict.orders && frm.fields_dict.orders.grid) {
      frm.fields_dict.orders.grid.get_field("item").get_query = function () {
        if (cust) return { filters: { customer: cust } };
        return {};
      };
    }

    // Items table (Warehouse Job Item)
    if (frm.fields_dict.items && frm.fields_dict.items.grid) {
      frm.fields_dict.items.grid.get_field("item").get_query = function () {
        if (cust) return { filters: { customer: cust } };
        return {};
      };
    }
  }

  // Optionally clear already-selected items if customer changes
  function clearItemsOnCustomerChange(frm) {
    const cust = frm.doc.customer || null;
    if (!cust) return;

    const clearRow = (row) => {
      if (row.item) {
        row.item = null;
        row.item_name = null;
        if ("uom" in row) row.uom = null;
        if ("serial_tracking" in row) row.serial_tracking = 0;
        if ("batch_tracking" in row) row.batch_tracking = 0;
        if ("sku_tracking" in row) row.sku_tracking = 0;
      }
    };

    (frm.doc.orders || []).forEach(clearRow);
    (frm.doc.items || []).forEach(clearRow);

    frm.refresh_field("orders");
    frm.refresh_field("items");
  }

  // ---------- Standard Actions ----------
  const allocatePick = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.allocate_pick",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Allocating picks…"),
      title: __("Allocation Result"),
      fallback: (res) =>
        __("Picks allocation finished. Created rows: {0}, Qty: {1}", [
          (res && res.created_rows) || 0,
          (res && res.created_qty) || 0,
        ]),
    });
  };

  const allocatePutaway = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.allocate_putaway",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Preparing putaway tasks…"),
      title: __("Putaway"),
      fallback: (res) =>
        __("Putaway prepared. Rows: {0}, Qty: {1}", [
          (res && res.created_rows) || 0,
          (res && res.created_qty) || 0,
        ]),
    });
  };

  const allocateMove = (frm) => {
    if (!ensureSaved(frm)) return;
    const d = new frappe.ui.Dialog({
      title: __("Allocate Move from Orders"),
      fields: [
        { fieldname: "clear_existing", label: __("Clear current Items before allocate"), fieldtype: "Check", default: 1 },
        {
          fieldname: "help",
          fieldtype: "HTML",
          options: `
            <div class="text-muted" style="margin-top:8px">
              • Reads <b>From/To</b> & HUs from the <b>Orders</b> table.<br>
              • Creates two <b>Items</b> rows per order: <i>−qty</i> from <b>From</b> and <i>+qty</i> to <b>To</b>.<br>
              • Requires: From/To locations present and quantity &gt; 0.
            </div>`,
        },
      ],
      primary_action_label: __("Allocate"),
      primary_action(values) {
        d.hide();
        frappe
          .call({
            method: "logistics.warehousing.api.allocate_move",
            args: { warehouse_job: frm.doc.name, clear_existing: values.clear_existing ? 1 : 0 },
            freeze: true,
            freeze_message: __("Allocating moves…"),
          })
          .then((r) => {
            const res = (r && r.message) || {};
            const msg =
              typeof res === "string"
                ? res
                : res.message || __("Move allocation complete. Pairs: {0}", [res.created_pairs || 0]);

            let html = `<div>${frappe.utils.escape_html(msg)}</div>`;
            if (res.skipped && res.skipped.length) {
              const lis = res.skipped.map((s) => `<li>${frappe.utils.escape_html(s)}</li>`).join("");
              html += `<div style="margin-top:8px">${__("Skipped")}:</div><ul>${lis}</ul>`;
            }
            frappe.msgprint({ title: __("Move Allocation"), message: html, indicator: "blue" });
            frm.reload_doc();
          })
          .catch((err) => {
            console.error(err);
            frappe.msgprint({
              title: __("Move Allocation Failed"),
              message: __("See console for details, or check server error logs."),
              indicator: "red",
            });
          });
      },
    });
    d.show();
  };

  // … (other functions unchanged: fetchCountSheet, createJobOperations, createAdjustments, createSalesInvoice, toggleBlindCountColumns) …

  // ---------- Button wiring & events ----------
  frappe.ui.form.on("Warehouse Job", {
    onload(frm) {
      applyItemCustomerFilter(frm);
    },

    refresh(frm) {
      applyItemCustomerFilter(frm);

      const t = frm.doc.type || "";
      const ds = frm.doc.docstatus || 0;
      addBtnIf(frm, t === "Pick" && ds < 2, __("Allocate Picks"), () => allocatePick(frm));
      addBtnIf(frm, t === "Putaway" && ds < 2, __("Allocate Putaway"), () => allocatePutaway(frm));
      addBtnIf(frm, t === "Move" && ds < 1, __("Allocate Move"), () => allocateMove(frm));
      // (other buttons unchanged)
    },

    customer(frm) {
      applyItemCustomerFilter(frm);
      clearItemsOnCustomerChange(frm);
    },
  });

  // … (VAS handlers, recalc_charge_total, Warehouse Job Charges events, Serial Management, etc. unchanged) …
})();
