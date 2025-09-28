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
      const payload = r && r.message ? r.message : {};
      const msg = extractMsg(r, fallback(payload));
      if (title) {
        frappe.msgprint({ title, message: msg, indicator: "blue" });
        if (typeof msg === "string") {
          frappe.show_alert({ message: `${title}: ${msg}`, indicator: "green" });
        }
      }
      try { frm.reload_doc(); } catch {}
      return payload;
    } catch (err) {
      console.error(err);
      frappe.msgprint({ title: __("Server Error"), message: __("See console for details."), indicator: "red" });
      throw err;
    }
  };

  const addBtnIf = (frm, cond, label, handler, group = GROUP_ACTION) => {
    if (!cond) return;
    frm.add_custom_button(label, () => handler(frm), group);
  };

  // ---------- Item filter by Customer ----------
  function applyItemCustomerFilter(frm) {
    const cust = frm.doc.customer || null;
    const setFilter = (grid, fieldname) => {
      if (!grid) return;
      const fld = grid.get_field(fieldname);
      if (fld) fld.get_query = () => (cust ? { filters: { customer: cust } } : {});
    };
    if (frm.fields_dict.orders?.grid) setFilter(frm.fields_dict.orders.grid, "item");
    if (frm.fields_dict.items?.grid)  setFilter(frm.fields_dict.items.grid,  "item");
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
    (frm.doc.items  || []).forEach(clearRow);
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

  // ---------- posting actions (batch) ----------
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

  // ---------- barcode camera ----------
  async function scan_barcode_with_camera() {
    try {
      if (window.erpnext?.utils?.scan_barcode) {
        const code = await erpnext.utils.scan_barcode();
        if (code) return String(code).trim();
      }
    } catch (e) { console.warn("erpnext.utils.scan_barcode failed:", e); }
    try {
      if (frappe.ui && typeof frappe.ui.Scanner === "function") {
        const code = await new Promise((resolve, reject) => {
          const scanner = new frappe.ui.Scanner({
            dialog: true,
            multiple: false,
            on_scan: (data) => resolve(String((data?.decodedText || data?.code || data?.content || data || "")).trim()),
            on_error: (err) => reject(err),
          });
          scanner.make?.();
          scanner.open?.();
        });
        if (code) return code;
      }
    } catch (e) { console.warn("frappe.ui.Scanner failed:", e); }
    try {
      if (frappe.ui && typeof frappe.ui.BarcodeScanner === "function") {
        const code = await new Promise((resolve, reject) => {
          const bs = new frappe.ui.BarcodeScanner({
            dialog: true,
            scan_action: (val) => resolve(String(val || "").trim()),
            on_error: (err) => reject(err),
          });
          bs.scan?.();
        });
        if (code) return code;
      }
    } catch (e) { console.warn("frappe.ui.BarcodeScanner failed:", e); }
    const v = await new Promise((resolve) => {
      frappe.prompt(
        [{ fieldname: "code", fieldtype: "Data", label: __("Barcode"), reqd: 1 }],
        (vals) => resolve(String(vals.code || "").trim()),
        __("Enter / Paste Barcode"),
        __("OK")
      );
    });
    return v;
  }

  function decorate_scan_field(dialog, fieldname) {
    const ctrl = dialog.get_field(fieldname);
    if (!ctrl?.$wrapper) return;
    ctrl.$input.attr("placeholder", __("Scan Barcode"));
    ctrl.$wrapper.addClass("barcode-scan-wrapper");

    const $btn = $(`<span class="btn btn-default btn-xs scan-inline-btn" title="${__("Scan with Camera")}">
        <i class="fa fa-qrcode"></i>
      </span>`).css({ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", cursor: "pointer", "z-index": 2 });

    ctrl.$wrapper.css("position", "relative");
    ctrl.$wrapper.find(".control-input").css("position", "relative");
    ctrl.$wrapper.append($btn);

    $btn.on("click", async (ev) => {
      ev.preventDefault();
      try {
        const code = await scan_barcode_with_camera();
        if (code) {
          dialog.set_value(fieldname, code);
          if (fieldname === "location_code") {
            dialog.get_field("handling_unit_code")?.$input?.focus();
          } else {
            dialog.get_primary_btn().focus();
          }
        }
      } catch (e) {
        console.error("Scan failed:", e);
        frappe.msgprint({ title: __("Scan Error"), message: __("Unable to read barcode. Please try again."), indicator: "red" });
      }
    });
  }

  const postByScan = (frm) => {
    if (!ensureSaved(frm)) return;
    if (!requireStaging(frm)) return;

    const d = new frappe.ui.Dialog({
      title: __("Post by Scan"),
      size: "small",
      fields: [
        { fieldtype: "Select", fieldname: "action", label: __("Action"),
          options: ["Receiving", "Putaway", "Pick", "Release"].join("\n"),
          default: ((t) => (t === "Putaway" ? "Putaway" : ((t === "Pick" || t === "VAS") ? "Pick" : "Pick")))((frm.doc.type || "").trim()),
          reqd: 1
        },
        { fieldtype: "Section Break", label: __("Scan Location") },
        { fieldtype: "Data", fieldname: "location_code", label: __("Scan Barcode"), reqd: 1, description: __("Location") },
        { fieldtype: "Section Break", label: __("Scan Handling Unit") },
        { fieldtype: "Data", fieldname: "handling_unit_code", label: __("Scan Barcode"), reqd: 1, description: __("Handling Unit") },
      ],
      primary_action_label: __("Post"),
      primary_action(values) {
        if (!values.location_code || !values.handling_unit_code || !values.action) {
          frappe.msgprint(__("Please select an Action and scan both Location and Handling Unit."));
          return;
        }
        d.hide();
        callServer(frm, {
          method: "logistics.warehousing.api.post_items_by_scan",
          args: {
            warehouse_job: frm.doc.name,
            action: values.action,
            location_code: values.location_code,
            handling_unit_code: values.handling_unit_code,
          },
          freezing: __("Posting by scan…"),
          title: __("Posted by Scan"),
          fallback: (m) => {
            const rows = (m && m.posted_rows) || 0;
            const q    = (m && m.posted_qty)  || 0;
            return __("Posted {0} rows, qty {1}.", [rows, q]);
          },
        });
      },
    });

    d.on_page_show = () => {
      decorate_scan_field(d, "location_code");
      decorate_scan_field(d, "handling_unit_code");

      const loc = d.get_field("location_code")?.$input;
      const hu  = d.get_field("handling_unit_code")?.$input;
      if (loc) {
        loc.on("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); hu?.focus(); } });
      }
      if (hu) {
        hu.on("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); d.get_primary_btn().click(); } });
      }
      loc?.focus();
    };

    d.show();
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

  // ---------- submit guard (status confirmation) ----------
  async function confirmNonAvailableLocationsBeforeSubmit(frm) {
    if (!frm.doc || !frm.doc.name) return true;

    const r = await frappe.call({
      method: "logistics.warehousing.api.check_item_location_statuses",
      args: { warehouse_job: frm.doc.name },
      freeze: true,
      freeze_message: __("Checking locations…"),
    });

    const data = r?.message || {};
    const hasWarnings = !!data.has_warnings;
    const locs = Array.isArray(data.affected_locations) ? data.affected_locations : [];
    const lines = Array.isArray(data.lines) ? data.lines : [];

    if (!hasWarnings || !locs.length) return true;

    // Build HTML: affected locations + per-row details
    const locsHtml = frappe.utils.escape_html(locs.join(", "));
    let table = "";
    if (lines.length) {
      const rows = lines.map((l) => `
        <tr>
          <td style="text-align:right;">${frappe.utils.escape_html(l.row_idx ?? "")}</td>
          <td>${frappe.utils.escape_html(l.field || "")}</td>
          <td>${frappe.utils.escape_html(l.location || "")}</td>
          <td>${frappe.utils.escape_html(l.status || "")}</td>
          <td>${frappe.utils.escape_html(l.item || "")}</td>
          <td style="text-align:right;">${frappe.format(l.qty || 0, { fieldtype: "Float" })}</td>
        </tr>`).join("");
      table = `
        <div class="mt-2">
          <div class="text-muted mb-2">${__("Affected rows")}</div>
          <div style="max-height: 260px; overflow:auto; border:1px solid var(--border-color); border-radius: var(--border-radius);">
            <table class="table table-bordered table-sm" style="margin:0;">
              <thead>
                <tr>
                  <th style="width:70px; text-align:right;">${__("Row")}</th>
                  <th style="width:120px;">${__("Field")}</th>
                  <th>${__("Location")}</th>
                  <th style="width:140px;">${__("Status")}</th>
                  <th>${__("Item")}</th>
                  <th style="width:100px; text-align:right;">${__("Qty")}</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>`;
    }

    const body = `
      <div>
        <p class="mb-2">${__("Some locations are not <b>Available</b>. Do you want to continue submitting?")}</p>
        <p><b>${__("Locations")}</b>: ${locsHtml}</p>
        ${table}
      </div>`;

    return await new Promise((resolve) => {
      // Use a dialog instead of frappe.confirm to avoid nested confirms on some browsers
      const d = new frappe.ui.Dialog({
        title: __("Location Status Warnings"),
        fields: [{ fieldtype: "HTML", fieldname: "body" }],
        primary_action_label: __("Continue Submit"),
        primary_action: () => { d.hide(); resolve(true); },
        secondary_action_label: __("Cancel"),
        secondary_action: () => { d.hide(); resolve(false); },
      });
      d.get_field("body").$wrapper.html(body);
      d.show();
    });
  }

  // ---------- form events ----------
  frappe.ui.form.on("Warehouse Job", {
    onload(frm) { applyItemCustomerFilter(frm); },
    customer(frm) { applyItemCustomerFilter(frm); clearItemsOnCustomerChange(frm); },

    refresh(frm) {
      applyItemCustomerFilter(frm);
      const t = (frm.doc.type || "").trim();
      const ds = frm.doc.docstatus || 0; // 0=draft, 1=submitted, 2=cancelled
      const not_cancelled = ds < 2;
      const not_submitted = ds < 1;
      const submitted = ds == 1;

      // Allocation
      addBtnIf(frm, t === "Pick"    && not_submitted, __("Allocate Picks"), allocatePick, GROUP_ACTION);
      addBtnIf(frm, t === "Putaway" && not_submitted, __("Allocate Putaway"), allocatePutaway, GROUP_ACTION);
      addBtnIf(frm, t === "Move"    && not_submitted, __("Allocate Move"), allocateMove, GROUP_ACTION);

      // Posting (batch + scan)
      if (submitted) {
        if (t === "Putaway") {
          addBtnIf(frm, true, __("Receiving"), postReceiving, GROUP_POST);
          addBtnIf(frm, true, __("Putaway"),   postPutaway,  GROUP_POST);
        } else if (t === "Pick" || t === "VAS") {
          addBtnIf(frm, true, __("Pick"),    postPick,    GROUP_POST);
          addBtnIf(frm, true, __("Release"), postRelease, GROUP_POST);
        }
        addBtnIf(frm, (t === "Putaway" || t === "Pick" || t === "VAS"), __("Post by Scan"), postByScan, GROUP_POST);
      }

      // Stocktake
      addBtnIf(frm, t === "Stocktake" && not_submitted, __("Fetch Count Sheet"), fetchCountSheet, GROUP_ACTION);
      addBtnIf(frm, t === "Stocktake" && not_submitted, __("Populate Adjustments"), createAdjustments, GROUP_ACTION);

      // Operations + Invoice
      addBtnIf(frm, not_submitted, __("Populate Operations"), populateOperations, GROUP_CREATE);
      addBtnIf(frm, not_cancelled, __("Create Sales Invoice"), createSalesInvoice, GROUP_CREATE);
    },

    // Intercept submit to ask the user instead of blocking, list affected locations.
    async before_submit(frm) {
      // One-time guard to avoid the “Permanently Submit … ?” repeat loop
      if (frm.__skip_location_check) return; // allow native submit to continue

      // Cancel this submit while we confirm
      frappe.validated = false;

      const ok = await confirmNonAvailableLocationsBeforeSubmit(frm);
      if (ok) {
        // Set guard and resubmit once
        frm.__skip_location_check = true;
        frm.savesubmit();
      } else {
        frappe.show_alert({ message: __("Submission cancelled."), indicator: "orange" });
      }
    },
  });

// ---- Charges grid auto pricing ----
frappe.ui.form.on("Warehouse Job Charges", {
  item_code(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!frm.doc || !frm.doc.name || !row.item_code) return;
    frappe.call({
      method: "logistics.warehousing.doctype.warehouse_job.warehouse_job.warehouse_job_fetch_charge_price",
      args: { warehouse_job: frm.doc.name, item_code: row.item_code },
      freeze: false,
    }).then((r) => {
      const msg = (r && r.message) || {};
      if (msg && typeof msg.rate !== "undefined") row.rate = msg.rate || 0;
      if (msg && msg.currency && "currency" in row) row.currency = msg.currency;
      // compute total after rate change
      const qty = flt(row.quantity || 0);
      const rate = flt(row.rate || 0);
      if ("total" in row) row.total = qty * rate;
      frm.refresh_field("charges");
    });
  },
  quantity(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const qty = flt(row.quantity || 0);
    const rate = flt(row.rate || 0);
    if ("total" in row) row.total = qty * rate;
    frm.refresh_field("charges");
  },
  rate(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const qty = flt(row.quantity || 0);
    const rate = flt(row.rate || 0);
    if ("total" in row) row.total = qty * rate;
    frm.refresh_field("charges");
  },
});

})();
