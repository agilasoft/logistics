// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transport Terminal', {
  setup(frm) {
    // Primary Contact query → only contacts linked to this Transport Terminal (server-side to avoid contact.link_doctype permission errors)
    frm.set_query('transportterminal_primary_contact', function (doc) {
      if (doc.__islocal || !doc.name) return { filters: { name: '__none__' } };
      let contact_names = [];
      frappe.call({
        method: 'logistics.contact_links.get_contact_names_for_dynamic_link',
        args: { link_doctype: 'Transport Terminal', link_name: doc.name },
        async: false,
        callback: function (r) { contact_names = r.message || []; }
      });
      return contact_names.length ? { filters: { name: ['in', contact_names] } } : { filters: { name: '__none__' } };
    });

    // Primary Address query → only addresses linked to this Transport Terminal
    frm.set_query('transportterminal_primary_address', function (doc) {
      if (doc.__islocal || !doc.name) return { filters: { name: '__none__' } };
      return {
        query: 'frappe.contacts.doctype.address.address.address_query',
        filters: { link_doctype: 'Transport Terminal', link_name: doc.name },
      };
    });
  },

  // Keep a formatted preview of the selected primary address (same as Customer)
  transportterminal_primary_address(frm) {
    if (frm.doc.transportterminal_primary_address) {
      frappe.call({
        method: 'frappe.contacts.doctype.address.address.get_address_display',
        args: {
          // Customer passes the name; method accepts a name or dict
          address_dict: frm.doc.transportterminal_primary_address,
        },
        callback: function (r) {
          frm.set_value('primary_address', r.message || '');
        },
      });
    } else {
      frm.set_value('primary_address', '');
    }
  },

  // Clear phone/mail if primary contact removed (parity with Customer's UX)
  transportterminal_primary_contact(frm) {
    if (!frm.doc.transportterminal_primary_contact) {
      // Add these fields to Transport Terminal if you want them synced
      if (frm.doc.mobile_no) frm.set_value('mobile_no', '');
      if (frm.doc.email_id) frm.set_value('email_id', '');
    }
  },

  refresh(frm) {
    if (!frm.doc.__islocal) {
      // Tell the renderer which doc we're on (same pattern many doctypes use)
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
