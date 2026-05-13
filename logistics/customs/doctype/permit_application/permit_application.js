// Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt

function _permit_application_date_constraints(frm) {
	const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
	const fields = ["approval_date", "rejection_date"];
	fields.forEach((fieldname) => {
		const c = frm.fields_dict[fieldname];
		if (!c || !c.datepicker) {
			return;
		}
		const opts = { maxDate: moment(today) };
		if (fieldname === "rejection_date" && frm.doc.approval_date) {
			opts.minDate = moment(frappe.datetime.str_to_obj(frm.doc.approval_date));
		}
		c.datepicker.update(opts);
	});
}

function _permit_status_preview_doc_args(frm) {
	return {
		name: frm.doc.name,
		status: frm.doc.status,
		approval_date: frm.doc.approval_date,
		rejection_date: frm.doc.rejection_date,
		valid_to: frm.doc.valid_to,
		valid_from: frm.doc.valid_from,
		renewal_of: frm.doc.renewal_of,
	};
}

/** Match server sync + expiry so Status updates without typing it. */
function _schedule_permit_status_preview(frm) {
	if (!frm) {
		return;
	}
	clearTimeout(frm._permit_status_preview_timer);
	frm._permit_status_preview_timer = setTimeout(() => _permit_application_status_preview(frm), 280);
}

function _permit_application_status_preview(frm) {
	frappe.call({
		method: "logistics.customs.doctype.permit_application.permit_application.preview_permit_application_status",
		args: { doc: _permit_status_preview_doc_args(frm) },
		callback(r) {
			const st = r.message && r.message.status;
			if (st != null && st !== frm.doc.status) {
				frm.set_value("status", st);
			}
		},
	});
}

/** Apply derived status from current field values (same rules as server validate). */
function _permit_application_apply_preview_status(frm) {
	return new Promise((resolve) => {
		frappe.call({
			method: "logistics.customs.doctype.permit_application.permit_application.preview_permit_application_status",
			args: { doc: _permit_status_preview_doc_args(frm) },
			callback(r) {
				if (r.exc) {
					resolve();
					return;
				}
				const st = r.message && r.message.status;
				if (st != null && st !== frm.doc.status) {
					const p = frm.set_value("status", st);
					if (p && p.then) {
						p.then(() => resolve()).catch(() => resolve());
					} else {
						resolve();
					}
				} else {
					resolve();
				}
			},
			error: () => resolve(),
		});
	});
}

frappe.ui.form.on("Permit Application", {
	refresh(frm) {
		if (cint(frm.doc.docstatus) === 0) {
			frm.set_intro(
				__(
					"Use Workflow: File, review, then Approve. Status updates from approval/rejection dates and Valid To. Frappe Submit runs on Approve."
				)
			);
		} else {
			frm.set_intro();
		}
		_permit_application_date_constraints(frm);
		_schedule_permit_status_preview(frm);
	},
	before_save(frm) {
		return _permit_application_apply_preview_status(frm);
	},
	approval_date(frm) {
		_permit_application_date_constraints(frm);
		_schedule_permit_status_preview(frm);
	},
	rejection_date(frm) {
		_permit_application_date_constraints(frm);
		_schedule_permit_status_preview(frm);
	},
	valid_to(frm) {
		_schedule_permit_status_preview(frm);
	},
	valid_from(frm) {
		_schedule_permit_status_preview(frm);
	},
	renewal_of(frm) {
		_schedule_permit_status_preview(frm);
	},
	status(frm) {
		// Workflow actions update status; re-derive from dates when applicable
		_schedule_permit_status_preview(frm);
	},
});
