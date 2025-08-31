// Parent doctype: Transport Operations Template
frappe.ui.form.on("Transport Operations Template", {
  refresh(frm) {
    // Child table fieldname = "instructions"
    frm.fields_dict["instructions"].grid.get_field("address").get_query = function (doc, cdt, cdn) {
      const row = locals[cdt][cdn];

      // Require a facility type before showing addresses
      if (!row.facility_type) {
        return { filters: [["Address", "name", "=", "__none__"]] };
      }

      // Match Address.custom_facility_type (Select) to row.facility_type (Select)
      return {
        filters: [
          ["Address", "custom_facility_type", "=", row.facility_type]
        ]
      };
    };
  }
});

// Child doctype: Transport Operations Template Instruction
frappe.ui.form.on("Transport Operations Template Instruction", {
  facility_type(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    // Clear address when facility type changes to avoid mismatches
    row.address = null;
    frm.refresh_field("instructions");
  }
});
