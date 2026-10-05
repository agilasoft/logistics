// Copy Annual Revenue when Create > Prospect builds the Prospect in the browser.
// ERPNext's LeadController.make_prospect copies organization fields but skips
// annual_revenue. The Opportunity server path does copy it.

(function () {
	if (!window.erpnext || !erpnext.LeadController || !erpnext.LeadController.prototype.make_prospect) {
		return;
	}
	if (erpnext.LeadController.prototype._logistics_make_prospect_patched) {
		return;
	}

	const original_make_prospect = erpnext.LeadController.prototype.make_prospect;

	erpnext.LeadController.prototype.make_prospect = function () {
		const annual_revenue = this.frm && this.frm.doc ? this.frm.doc.annual_revenue : null;
		const original_with_doctype = frappe.model.with_doctype;
		let restored = false;

		function restore_with_doctype() {
			if (!restored) {
				frappe.model.with_doctype = original_with_doctype;
				restored = true;
			}
		}

		frappe.model.with_doctype = function (doctype, callback, async_flag) {
			restore_with_doctype();
			return original_with_doctype.call(
				frappe.model,
				doctype,
				function () {
					const original_get_new_doc = frappe.model.get_new_doc;
					frappe.model.get_new_doc = function (new_doctype) {
						frappe.model.get_new_doc = original_get_new_doc;
						const doc = original_get_new_doc.apply(this, arguments);
						if (new_doctype === "Prospect" && annual_revenue) {
							doc.annual_revenue = annual_revenue;
						}
						return doc;
					};
					try {
						return callback && callback.apply(this, arguments);
					} finally {
						frappe.model.get_new_doc = original_get_new_doc;
					}
				},
				async_flag
			);
		};

		try {
			return original_make_prospect.apply(this, arguments);
		} finally {
			restore_with_doctype();
		}
	};

	erpnext.LeadController.prototype._logistics_make_prospect_patched = true;
})();
