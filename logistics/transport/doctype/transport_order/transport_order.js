// logistics/transport/doctype/transport_order/transport_order.js
frappe.ui.form.on('Transport Order', {
  refresh(frm) {
    // Show the action only when NOT submitted
    if (frm.doc.docstatus !== 1) {
      frm.add_custom_button(__('Get Leg Plan'), async () => {
        if (!frm.doc.transport_template) {
          frappe.msgprint(__('Please select a Transport Template first.'));
          return;
        }

        const run = async () => {
          frappe.call({
            method: 'logistics.transport.doctype.transport_order.transport_order.action_get_leg_plan',
            args: { docname: frm.doc.name, replace: 1, save: 1 },
            freeze: true,
            freeze_message: __('Fetching legs from Transport Template...'),
            callback: (r) => {
              if (r && r.message) {
                const { template, added, cleared } = r.message;
                frappe.show_alert({
                  message: __(`Leg Plan updated from <b>${template}</b>: cleared ${cleared}, added ${added}.`),
                  indicator: 'green'
                });
              }
              frm.reload_doc();
            }
          });
        };

        if (frm.is_dirty()) {
          await frm.save();
        }
        await run();
      }, __('Actions'));
    }
  }
});

frappe.ui.form.on('Transport Order', {
  refresh(frm) {
    // Only when submitted
    if (frm.doc.docstatus === 1) {
      frm.add_custom_button(__('Transport Job'), () => {
        frappe.call({
          method: 'logistics.transport.doctype.transport_order.transport_order.action_create_transport_job',
          args: { docname: frm.doc.name },
          freeze: true,
          freeze_message: __('Creating Transport Job...'),
          callback: (r) => {
            if (!r || !r.message) return;
            const { name, created, already_exists } = r.message;

            if (already_exists) {
              frappe.msgprint(
                __('Transport Job already exists: {0}', [name])
              );
            } else if (created) {
              frappe.show_alert({
                message: __('Transport Job {0} created.', [name]),
                indicator: 'green'
              });
            }
            frappe.set_route('Form', 'Transport Job', name);
          }
        });
      }, __('Create'));
    }
  }
});
