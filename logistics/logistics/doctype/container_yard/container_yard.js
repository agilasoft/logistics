frappe.ui.form.on('Container Yard', {
  setup(frm) {
    // Primary Contact query → only contacts linked to this Container Yard
    frm.set_query('containeryard_primary_contact', function (doc) {
      return {
        filters: {
          link_doctype: 'Container Yard',
          link_name: doc.name
        },
      };
    });

    // Primary Address query → only addresses linked to this Container Yard
    frm.set_query('containeryard_primary_address', function (doc) {
      return {
        filters: {
          link_doctype: 'Container Yard',
          link_name: doc.name
        },
      };
    });
  },

  // Keep a formatted preview of the selected primary address (same as Customer)
  containeryard_primary_address(frm) {
    if (frm.doc.containeryard_primary_address) {
      frappe.call({
        method: 'frappe.contacts.doctype.address.address.get_address_display',
        args: {
          // Customer passes the name; method accepts a name or dict
          address_dict: frm.doc.containeryard_primary_address,
        },
        callback: function (r) {
          frm.set_value('primary_address', r.message || '');
        },
      });
    } else {
      frm.set_value('primary_address', '');
    }
  },

  // Clear phone/mail if primary contact removed (parity with Customer’s UX)
  containeryard_primary_contact(frm) {
    if (!frm.doc.containeryard_primary_contact) {
      // Add these fields to Container Yard if you want them synced
      if (frm.doc.mobile_no) frm.set_value('mobile_no', '');
      if (frm.doc.email_id) frm.set_value('email_id', '');
    }
  },

  refresh(frm) {
    if (!frm.doc.__islocal) {
      // Tell the renderer which doc we’re on (same pattern many doctypes use)
      frappe.dynamic_link = {
        doc: frm.doc,
        fieldname: 'name',
        doctype: frm.doctype,
      };

      // This is what Customer uses in v15
      frappe.contacts.render_address_and_contact(frm);
    } else {
      // New unsaved doc → clear panels (same as Customer)
      frappe.contacts.clear_address_and_contact(frm);
    }
  },
});
