// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// ---------------------------- Inbound Order (Parent) ----------------------------
frappe.ui.form.on('Inbound Order', {
  refresh(frm) {
    // Create → Warehouse Job button (only when submitted)
    if (!frm.doc.__islocal && frm.doc.docstatus === 1) {
      frm.add_custom_button(
        __('Warehouse Job'),
        function () {
          frappe.model.open_mapped_doc({
            method: "logistics.warehousing.doctype.inbound_order.inbound_order.make_warehouse_job",
            frm: frm
          });
        },
        __('Create')
      );
    }

    // Create → Serials & Batches manual button (when not new)
    if (!frm.is_new()) {
      frm.add_custom_button(
        __('Serials & Batches'),
        () => run_serials_and_batches(frm, { show_summary: true }),
        __('Create')
      );
    }
  },

  onload(frm) {
    maybe_set_planned_date(frm);
  },

  before_save(frm) {
    if (!frm.doc.planned_date) maybe_set_planned_date(frm, true);
  },

  // Auto-run Serials & Batches right before submit
  // (ensures newly typed serial/batch text is materialized/linked at submission)
  async before_submit(frm) {
    await run_serials_and_batches(frm, { show_summary: false, throw_on_error: true });
  },

  // When a new row is added to the charges table, initialize total
  // NOTE: If your table fieldname ≠ "charges", rename this event to <your_fieldname>_add
  charges_add(frm, cdt, cdn) {
    recalc_charge_total(cdt, cdn);
  },

  // Safety net: recompute all charge totals on validate (covers paste/import edits)
  validate(frm) {
    (frm.doc.charges || []).forEach(row => {
      const qty  = parseFloat(row.quantity) || 0;
      const rate = parseFloat(row.rate) || 0;
      row.total = qty * rate;
    });
    frm.refresh_field("charges");
  }
});

// ---------------------------- Contract Charge Helpers ----------------------------
function _resolve_item(row) {
  return row.charge_item || row.item_code || row.item || row.item_charge;
}

function _apply_vals(cdt, cdn, m) {
  if (!m) return;

  if (typeof m.rate === "number") frappe.model.set_value(cdt, cdn, "rate", m.rate);
  if (m.currency) frappe.model.set_value(cdt, cdn, "currency", m.currency);

  // strictly use UOM from Contract
  const contract_uom = (m.storage_charge && m.storage_uom) ? m.storage_uom : (m.handling_uom || null);
  if (contract_uom) {
    frappe.model.set_value(cdt, cdn, "uom", contract_uom);
  } else {
    // ensure Item default doesn't stick
    frappe.model.set_value(cdt, cdn, "uom", "");
    frappe.show_alert({ message: __("No UOM set on Warehouse Contract for this charge."), indicator: "orange" });
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

frappe.ui.form.on("Inbound Order Charges", {
  charge_item(frm, cdt, cdn) { _fetch(frm, cdt, cdn, "inbound"); },
  item_code(frm, cdt, cdn)  { _fetch(frm, cdt, cdn, "inbound"); },

  // auto-calc total when editing charge lines
  quantity(frm, cdt, cdn)   { recalc_charge_total(cdt, cdn); },
  rate(frm, cdt, cdn)       { recalc_charge_total(cdt, cdn); },
});

// ---------------------------- Serials & Batches ----------------------------
async function run_serials_and_batches(frm, opts = {}) {
  const { show_summary = true, throw_on_error = false } = opts;

  // quick escape if no items
  if (!(frm.doc.items || []).length) return;

  try {
    const r = await frappe.call({
      method: 'logistics.warehousing.api.create_serial_and_batch_for_inbound',
      args: { inbound_order: frm.doc.name },
      freeze: true,
      freeze_message: __('Creating / linking Serials & Batches...'),
    });

    const m = r.message || {};
    if (show_summary) {
      const summary = [
        __('Created Serials: {0}', [m.created?.serial || 0]),
        __('Created Batches: {0}', [m.created?.batch || 0]),
        __('Linked Serials: {0}', [m.linked?.serial || 0]),
        __('Linked Batches: {0}', [m.linked?.batch || 0]),
        __('Skipped: {0}', [m.skipped || 0]),
        (m.errors && m.errors.length ? __('Errors: {0}', [m.errors.length]) : '')
      ].filter(Boolean).join('<br>');
      frappe.msgprint({ title: __('Serials & Batches'), message: summary, indicator: (m.errors?.length ? 'orange' : 'blue') });
    }

    // Always reload to reflect any created/linked records
    await frm.reload_doc();

    // If we’re in before_submit and there were errors, block submission
    if (throw_on_error && m.errors && m.errors.length) {
      frappe.throw(__('Could not finalize Serials & Batches. Please review the items and try again.'));
    }
  } catch (e) {
    if (throw_on_error) {
      // Block submit with a clear error
      frappe.throw(__('Failed to create/link Serials & Batches: {0}', [e.message || e]));
    } else {
      frappe.msgprint({
        title: __('Serials & Batches'),
        message: __('Failed to create/link: {0}', [e.message || e]),
        indicator: 'red'
      });
    }
  }
}

// ---------------------------- Planned Date Helper ----------------------------
function maybe_set_planned_date(frm, force = false) {
  if (!force && (frm.doc.planned_date || frm.__planned_date_set)) return;

  frappe.db.get_single_value("Warehouse Settings", "planned_date_offset_days")
    .then((val) => {
      const offset = parseInt(val, 10) || 0;
      const nowStr = frappe.datetime.now_datetime(); // "YYYY-MM-DD HH:mm:ss"
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
    // Pure JS fallback
    const d = new Date(baseStr.replace(" ", "T"));
    d.setDate(d.getDate() + days);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
}

// ---------------------------- Charges Math ----------------------------
function recalc_charge_total(cdt, cdn) {
  const row  = locals[cdt][cdn];
  const qty  = parseFloat(row.quantity) || 0;
  const rate = parseFloat(row.rate) || 0;
  frappe.model.set_value(cdt, cdn, "total", qty * rate);
}

// ---------------------------- Inbound Order Item rules ----------------------------
frappe.ui.form.on("Inbound Order Item", {
  serial_tracking(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
    }
    // ensure grid re-evaluates read_only_depends_on per row
    frm.fields_dict.items.grid.refresh();
  },

  quantity(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (row.serial_tracking && row.quantity != 1) {
      frappe.model.set_value(cdt, cdn, "quantity", 1);
      frappe.show_alert(__("Serial-tracked items must have Quantity = 1"));
    }
  }
});
