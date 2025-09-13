// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Warehouse Item", {
// 	refresh(frm) {

// 	},
// });

// DocType: Warehouse Item
frappe.ui.form.on('Warehouse Item', {
  refresh(frm) {
    // Enforce once on load/refresh in case of imports or programmatic changes
    enforce_mutual_exclusivity(frm);
  },

  serial_tracking(frm) {
    if (cbool(frm.doc.serial_tracking)) {
      if (cbool(frm.doc.batch_tracking)) {
        frm.set_value('batch_tracking', 0);
      }
      frappe.show_alert({ message: __('Serial Tracking enabled — Batch Tracking auto-disabled'), indicator: 'blue' });
    }
  },

  batch_tracking(frm) {
    if (cbool(frm.doc.batch_tracking)) {
      if (cbool(frm.doc.serial_tracking)) {
        frm.set_value('serial_tracking', 0);
      }
      frappe.show_alert({ message: __('Batch Tracking enabled — Serial Tracking auto-disabled'), indicator: 'blue' });
    }
  },

  validate(frm) {
    // Final gate: throw if both somehow remain true (e.g., via API/script)
    if (cbool(frm.doc.serial_tracking) && cbool(frm.doc.batch_tracking)) {
      frappe.throw(__('Serial Tracking and Batch Tracking cannot both be enabled at the same time.'));
    }
  }
});

// ---------- Helpers ----------
function cbool(v) {
  // Frappe may pass "0"/"1", 0/1, false/true; normalize to boolean
  return (v === 1 || v === '1' || v === true);
}

function enforce_mutual_exclusivity(frm) {
  // If both are checked (from data import or server update), uncheck batch by default
  if (cbool(frm.doc.serial_tracking) && cbool(frm.doc.batch_tracking)) {
    frm.set_value('batch_tracking', 0);
    frappe.show_alert({ message: __('Both tracking flags were set — Batch Tracking auto-disabled'), indicator: 'orange' });
  }
}
