// logistics/transport/doctype/transport_plan/transport_plan.js
frappe.ui.form.on('Transport Plan', {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__('Run Sheets'), () => {
        frappe.call({
          method: 'logistics.transport.doctype.transport_plan.transport_plan.auto_allocate_and_create',
          args: { plan_name: frm.doc.name },
          freeze: true,
          freeze_message: __('Allocating and creating Run Sheets…'),
        }).then(r => {
          const res = r.message || {};
          const created = res.created || [];
          const skipped = res.skipped || [];
          const errors  = res.errors  || [];

          let html = `<div><b>${__('Created')}:</b> ${created.length}</div>`;
          if (created.length) {
            html += `<ul>${created.map(n =>
              `<li><a href="#Form/Run Sheet/${encodeURIComponent(n)}">${frappe.utils.escape_html(n)}</a></li>`
            ).join('')}</ul>`;
          }

          if (skipped.length) {
            html += `<div class="mt-3"><b>${__('Skipped')}:</b> ${skipped.length}</div>`;
            html += `<ul>${skipped.map(x =>
              `<li>${frappe.utils.escape_html(x.leg || '-')} — ${frappe.utils.escape_html(x.reason || '')}</li>`
            ).join('')}</ul>`;
          }

          if (errors.length) {
            html += `<div class="mt-3 text-danger"><b>${__('Errors')}:</b></div>`;
            html += `<ul>${errors.map(e =>
              `<li>${frappe.utils.escape_html(e)}</li>`
            ).join('')}</ul>`;
          }

          frappe.msgprint({
            title: __('Create ➜ Run Sheets'),
            message: html,
            indicator: errors.length ? 'red' : (created.length ? 'green' : 'orange'),
            wide: true,
          });

          frm.reload_doc();
        }).catch(() => {
          frappe.msgprint({
            title: __('Create ➜ Run Sheets'),
            message: __('Something went wrong while allocating. Check Error Log.'),
            indicator: 'red',
          });
        });
      }, __('Create'));
    }
  }
});
