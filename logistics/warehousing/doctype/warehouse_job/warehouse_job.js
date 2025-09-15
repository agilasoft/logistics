// Copyright (c) 2025, www.agilasoft.com
// For license information, please see license.txt

(() => {
  const GROUP_ACTION = __("Action");
  const GROUP_CREATE = __("Create");
  const GROUP_POST   = __("Post");

  // ---------- helpers ----------
  const ensureSaved = (f) => {
    const frm = f || (typeof cur_frm !== "undefined" ? cur_frm : null);
    if (!frm || !frm.doc) {
      console.error("[Warehouse Job] Missing frm in ensureSaved()");
      frappe.msgprint(__("Unexpected error: form not ready. Try reloading the page."));
      return false;
    }
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

  const callServer = async (
    frm,
    { method, args = {}, freeze = true, freezing = __("Working…"), title = __("Result"), fallback = () => "" }
  ) => {
    try {
      const r = await frappe.call({ method, args, freeze, freeze_message: freezing });
      const msg = extractMsg(r, fallback(r && r.message ? r.message : {}));
      frappe.msgprint({ title, message: msg, indicator: "blue" });
      // show toast as well
      if (typeof msg === "string") {
        frappe.show_alert({ message: `${title}: ${msg}`, indicator: "green" });
      }
      frm.reload_doc();
      return r && r.message;
    } catch (err) {
      console.error(err);
      frappe.msgprint({ title: __("Server Error"), message: __("See console for details."), indicator: "red" });
      throw err;
    }
  };

  // ALWAYS wrap the click handler so frm is passed in
  const addBtnIf = (frm, cond, label, handler, group = GROUP_ACTION) => {
    if (!cond) return;
    frm.add_custom_button(label, () => handler(frm), group);
  };

  // ---------- Item filter by Customer ----------
  function applyItemCustomerFilter(frm) {
    const cust = frm.doc.customer || null;

    // Orders table
    if (frm.fields_dict.orders && frm.fields_dict.orders.grid) {
      const fld = frm.fields_dict.orders.grid.get_field("item");
      if (fld) {
        fld.get_query = function () {
          return cust ? { filters: { customer: cust } } : {};
        };
      }
    }

    // Items table
    if (frm.fields_dict.items && frm.fields_dict.items.grid) {
      const fld = frm.fields_dict.items.grid.get_field("item");
      if (fld) {
        fld.get_query = function () {
          return cust ? { filters: { customer: cust } } : {};
        };
      }
    }
  }

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

  // ---------- allocation actions ----------
  const allocatePick = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.allocate_pick",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Allocating picks…"),
      title: __("Allocate Picks"),
      fallback: (res) =>
        __("Allocated {0} units across {1} pick rows.", [
          (res && res.created_qty) || 0,
          (res && res.created_rows) || 0,
        ]),
    });
  };

  const allocatePutaway = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.allocate_putaway",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Preparing putaway…"),
      title: __("Allocate Putaway"),
      fallback: (res) =>
        __("Prepared {0} units across {1} putaway rows.", [
          (res && res.created_qty) || 0,
          (res && res.created_rows) || 0,
        ]),
    });
  };

  const allocateMove = (frm) => {
    if (!ensureSaved(frm)) return;
    const d = new frappe.ui.Dialog({
      title: __("Allocate Move from Orders"),
      fields: [{ fieldname: "clear_existing", label: __("Clear current Items before allocate"), fieldtype: "Check", default: 1 }],
      primary_action_label: __("Allocate"),
      primary_action(values) {
        d.hide();
        callServer(frm, {
          method: "logistics.warehousing.api.allocate_move",
          args: { warehouse_job: frm.doc.name, clear_existing: values.clear_existing ? 1 : 0 },
          freezing: __("Allocating moves…"),
          title: __("Allocate Move"),
          fallback: (res) => __("Allocated {0} move pair(s).", [(res && res.created_pairs) || 0]),
        });
      },
    });
    d.show();
  };

  // ---------- posting actions (new flow) ----------
  const requireStaging = (frm) => {
    if (!frm.doc.staging_area) {
      frappe.msgprint(__("Please set a Staging Area on this Job first."));
      return false;
    }
    return true;
  };

  const postReceiving = (frm) => {
    if (!ensureSaved(frm) || !requireStaging(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.post_receiving",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Posting receiving into staging…"),
      title: __("Receiving Posted"),
    });
  };

  const postPutaway = (frm) => {
    if (!ensureSaved(frm) || !requireStaging(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.post_putaway",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Posting putaway movements…"),
      title: __("Putaway Posted"),
    });
  };

  const postPick = (frm) => {
    if (!ensureSaved(frm) || !requireStaging(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.post_pick",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Posting pick movements…"),
      title: __("Pick Posted"),
    });
  };

  const postRelease = (frm) => {
    if (!ensureSaved(frm) || !requireStaging(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.post_release",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Posting release from staging…"),
      title: __("Release Posted"),
    });
  };

  // ---------- stocktake ----------
  const fetchCountSheet = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.warehouse_job_fetch_count_sheet",
      args: { warehouse_job: frm.doc.name, clear_existing: 1 },
      freezing: __("Building count sheet…"),
      title: __("Count Sheet"),
    });
  };

  const createAdjustments = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.populate_stocktake_adjustments",
      args: { warehouse_job: frm.doc.name, clear_existing: 1 },
      freezing: __("Creating adjustments…"),
      title: __("Adjustments"),
    });
  };

  // ---------- operations ----------
  const populateOperations = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.populate_job_operations",
      args: { warehouse_job: frm.doc.name, clear_existing: 1 },
      freezing: __("Populating operations…"),
      title: __("Operations"),
    });
  };

  // ---------- invoice ----------
  const createSalesInvoice = (frm) => {
    if (!ensureSaved(frm)) return;
    callServer(frm, {
      method: "logistics.warehousing.api.create_sales_invoice_from_job",
      args: { warehouse_job: frm.doc.name },
      freezing: __("Creating Sales Invoice…"),
      title: __("Sales Invoice"),
      fallback: (m) => (m && m.sales_invoice ? __("Created Sales Invoice {0}", [m.sales_invoice]) : __("Sales Invoice created.")),
    });
  };

  // ---------- form events ----------
  frappe.ui.form.on("Warehouse Job", {
    onload(frm) {
      applyItemCustomerFilter(frm);
    },

    customer(frm) {
      applyItemCustomerFilter(frm);
      clearItemsOnCustomerChange(frm);
    },

    refresh(frm) {
      applyItemCustomerFilter(frm);

      const t = (frm.doc.type || "").trim();
      const ds = frm.doc.docstatus || 0; // 0=draft, 1=submitted, 2=cancelled
      const not_cancelled = ds < 2;

      // Allocation
      addBtnIf(frm, t === "Pick"    && not_cancelled, __("Allocate Picks"), allocatePick, GROUP_ACTION);
      addBtnIf(frm, t === "Putaway" && not_cancelled, __("Allocate Putaway"), allocatePutaway, GROUP_ACTION);
      addBtnIf(frm, t === "Move"    && not_cancelled, __("Allocate Move"), allocateMove, GROUP_ACTION);

      // Posting (new flow)
      if (not_cancelled) {
        if (t === "Putaway") {
          addBtnIf(frm, true, __("Receiving"), postReceiving, GROUP_POST);
          addBtnIf(frm, true, __("Putaway"),   postPutaway,  GROUP_POST);
        } else if (t === "Pick" || t === "VAS") {
          addBtnIf(frm, true, __("Pick"),    postPick,    GROUP_POST);
          addBtnIf(frm, true, __("Release"), postRelease, GROUP_POST);
        }
      }

      // Stocktake
      addBtnIf(frm, t === "Stocktake" && not_cancelled, __("Fetch Count Sheet"), fetchCountSheet, GROUP_ACTION);
      addBtnIf(frm, t === "Stocktake" && not_cancelled, __("Populate Adjustments"), createAdjustments, GROUP_ACTION);

      // Operations + Invoice
      addBtnIf(frm, not_cancelled, __("Populate Operations"), populateOperations, GROUP_CREATE);
      addBtnIf(frm, not_cancelled, __("Create Sales Invoice"), createSalesInvoice, GROUP_CREATE);
    },
  });
})();
