// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Number", {
	job_type(frm) {
		frm.set_value("project", null);
	},

	job_no(frm) {
		fetch_project_from_source(frm);
	},
});

function fetch_project_from_source(frm) {
	if (!frm.doc.job_type || !frm.doc.job_no) {
		return;
	}

	const source_doctype = frm.doc.job_type === "Docket" ? "Docket" : frm.doc.job_type;

	frappe.model.with_doctype(source_doctype, function () {
		const meta = frappe.get_meta(source_doctype);
		const has_project = !!(
			meta &&
			(meta.fields || []).find(function (df) {
				return df.fieldname === "project";
			})
		);
		if (!has_project) {
			return;
		}
		frappe.db.get_value(source_doctype, frm.doc.job_no, "project").then(function (r) {
			const project = r && r.message && r.message.project;
			if (project) {
				frm.set_value("project", project);
			}
		});
	});
}
