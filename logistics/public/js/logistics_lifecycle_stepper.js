// Copyright (c) 2026, Agilasoft and contributors
// Lifecycle stage link queries for Special Project, Exhibit, and Sales Quote.

frappe.provide("logistics.lifecycle");

logistics.lifecycle._module_filter = function (frm) {
	if (frm.doctype === "Exhibit") {
		return "for_exhibits";
	}
	return "for_special_project";
};

logistics.lifecycle.LIFECYCLE_JOB_LINK_FIELDS = ["job_type", "job_no"];

logistics.lifecycle._strip_lifecycle_job_link_fields = function (row) {
	if (!row) {
		return row;
	}
	logistics.lifecycle.LIFECYCLE_JOB_LINK_FIELDS.forEach(function (fieldname) {
		row[fieldname] = null;
	});
	return row;
};

/** Shallow clone for grid duplicate; must not mutate the source row. */
logistics.lifecycle._clone_row_without_job_link = function (copy_doc) {
	if (!copy_doc) {
		return copy_doc;
	}
	var clone = Object.assign({}, copy_doc);
	return logistics.lifecycle._strip_lifecycle_job_link_fields(clone);
};

/**
 * Grid "Duplicate" uses grid.duplicate_row, which ignores DocField no_copy.
 * Also patch add_new_row so copy_doc never carries job_type/job_no into the new row.
 */
logistics.lifecycle.patch_grid_duplicate_respects_no_copy = function (frm, table_fieldname) {
	var field = frm.fields_dict[table_fieldname];
	if (!field || !field.grid) {
		return false;
	}
	var grid = field.grid;
	var child_doctype = field.df.options;
	if (grid._logistics_lifecycle_duplicate_patched) {
		return true;
	}
	grid._logistics_lifecycle_duplicate_patched = true;

	var orig_add_new_row = grid.add_new_row.bind(grid);
	grid.add_new_row = function (idx, callback, show, copy_doc, go_to_last_page, go_to_first_page) {
		if (copy_doc && child_doctype === "Lifecycle Job") {
			copy_doc = logistics.lifecycle._clone_row_without_job_link(copy_doc);
		}
		return orig_add_new_row(idx, callback, show, copy_doc, go_to_last_page, go_to_first_page);
	};

	var orig_duplicate_row = grid.duplicate_row.bind(grid);
	grid.duplicate_row = function (d, copy_doc) {
		if (copy_doc && child_doctype === "Lifecycle Job") {
			copy_doc = logistics.lifecycle._clone_row_without_job_link(copy_doc);
		}
		orig_duplicate_row(d, copy_doc);
		(frappe.meta.get_docfields(child_doctype) || []).forEach(function (df) {
			if (cint(df.no_copy)) {
				d[df.fieldname] = df.fieldtype === "Check" ? 0 : null;
			}
		});
		if (child_doctype === "Lifecycle Job") {
			logistics.lifecycle._strip_lifecycle_job_link_fields(d);
		}
		return d;
	};
	return true;
};

logistics.lifecycle.clear_lifecycle_job_link_on_row_add = function (frm, cdt, cdn) {
	if (!cdt || !cdn || cdt !== "Lifecycle Job") {
		return;
	}
	var row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	var had_link = row.job_type || row.job_no;
	logistics.lifecycle._strip_lifecycle_job_link_fields(row);
	if (!had_link) {
		return;
	}
	var grid = frm.fields_dict.lifecycle_jobs && frm.fields_dict.lifecycle_jobs.grid;
	if (!grid || !grid.grid_rows_by_docname) {
		return;
	}
	var grid_row = grid.grid_rows_by_docname[cdn];
	if (grid_row) {
		grid_row.refresh_field("job_type");
		grid_row.refresh_field("job_no");
	}
};

logistics.lifecycle.setup_queries = function (frm) {
	var moduleFilter = logistics.lifecycle._module_filter(frm);
	var filters = {};
	filters[moduleFilter] = 1;

	if (frm.fields_dict.lifecycle_stage) {
		frm.set_query("lifecycle_stage", function () {
			return { filters: filters };
		});
	}

	if (frm.fields_dict.internal_job_details) {
		frm.set_query("lifecycle_stage", "internal_job_details", function () {
			return {
				filters: Object.assign({}, filters, { is_closed: 0 }),
			};
		});
	}
};

/** Call from parent form refresh once the lifecycle_jobs grid exists. */
logistics.lifecycle.setup_lifecycle_jobs_grid = function (frm) {
	if (!frm.fields_dict.lifecycle_jobs) {
		return;
	}
	if (logistics.lifecycle.patch_grid_duplicate_respects_no_copy(frm, "lifecycle_jobs")) {
		return;
	}
	if (frm._lifecycle_jobs_duplicate_patch_retry) {
		return;
	}
	frm._lifecycle_jobs_duplicate_patch_retry = true;
	setTimeout(function () {
		logistics.lifecycle.patch_grid_duplicate_respects_no_copy(frm, "lifecycle_jobs");
	}, 300);
};
