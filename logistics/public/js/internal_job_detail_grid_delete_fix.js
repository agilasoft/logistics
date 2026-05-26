// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt
//
// Frappe Grid.delete_rows() calls grid_row.remove() without awaiting its async
// run_serially chain. Parallel clear_doc() calls on the same parent child table
// can read a stale rows array and resurrect rows that were already removed —
// users see "Delete row" add or restore lines instead of removing them.
//
// Patch delete_rows for Internal Job Detail child grids to remove all selected
// rows in one pass, then refresh once.
//
// Grid "Duplicate" ignores DocField no_copy; strip job_type and job_no so a
// duplicated line does not reuse an existing internal job link.

(function patch_internal_job_detail_grid_delete() {
	"use strict";

	var IJ_CHILD_DOCTYPE = "Internal Job Detail";
	var IJ_JOB_LINK_FIELDS = ["job_type", "job_no"];
	var JOB_TYPE_BY_SERVICE = {
		Air: "Air Booking",
		Sea: "Sea Booking",
		Transport: "Transport Order",
		Customs: "Declaration Order",
		Warehousing: "Inbound Order",
		"Special Project": "Project Order",
	};

	function is_internal_job_detail_grid(grid) {
		return grid && grid.df && grid.df.options === IJ_CHILD_DOCTYPE;
	}

	function strip_ij_job_link_fields(row) {
		if (!row) {
			return row;
		}
		row.job_no = null;
		row.job_type = null;
		return row;
	}

	function sync_job_type_from_service(row) {
		if (!row) {
			return row;
		}
		var jt = JOB_TYPE_BY_SERVICE[String(row.service_type || "").trim()];
		if (jt) {
			row.job_type = jt;
		}
		return row;
	}

	function clone_row_without_job_link(copy_doc) {
		if (!copy_doc) {
			return copy_doc;
		}
		return strip_ij_job_link_fields(Object.assign({}, copy_doc));
	}

	function refresh_ij_job_link_fields(grid, d) {
		if (!grid || !grid.grid_rows_by_docname || !d || !d.name) {
			return;
		}
		var grid_row = grid.grid_rows_by_docname[d.name];
		if (!grid_row) {
			return;
		}
		IJ_JOB_LINK_FIELDS.forEach(function (fieldname) {
			grid_row.refresh_field(fieldname);
		});
	}

	function patch_internal_job_detail_grid_duplicate(grid) {
		if (!is_internal_job_detail_grid(grid) || grid._logistics_ij_duplicate_patched) {
			return;
		}
		grid._logistics_ij_duplicate_patched = true;

		var orig_add_new_row = grid.add_new_row.bind(grid);
		grid.add_new_row = function (idx, callback, show, copy_doc, go_to_last_page, go_to_first_page) {
			if (copy_doc) {
				copy_doc = clone_row_without_job_link(copy_doc);
			}
			return orig_add_new_row(
				idx,
				callback,
				show,
				copy_doc,
				go_to_last_page,
				go_to_first_page
			);
		};

		var orig_duplicate_row = grid.duplicate_row.bind(grid);
		grid.duplicate_row = function (d, copy_doc) {
			if (copy_doc) {
				copy_doc = clone_row_without_job_link(copy_doc);
			}
			orig_duplicate_row(d, copy_doc);
			strip_ij_job_link_fields(d);
			sync_job_type_from_service(d);
			refresh_ij_job_link_fields(grid, d);
			return d;
		};
	}

	function delete_selected_rows_sync(grid) {
		var frm = grid.frm;
		if (!frm) {
			return;
		}
		var fieldname = grid.df.fieldname;
		var selected = grid.get_selected_children().slice();
		if (!selected.length) {
			return;
		}

		var before_tasks = selected.map(function (doc) {
			return function () {
				return frm.script_manager.trigger(
					"before_" + fieldname + "_remove",
					doc.doctype,
					doc.name
				);
			};
		});

		frappe
			.run_serially(before_tasks)
			.then(function () {
				selected.forEach(function (doc) {
					frappe.model.clear_doc(doc.doctype, doc.name);
				});
				selected.forEach(function (doc) {
					frm.script_manager.trigger(fieldname + "_remove", doc.doctype, doc.name);
				});
				grid.refresh();
				frm.dirty();
				frm.script_manager.trigger(fieldname + "_delete", grid.doctype);

				grid.wrapper
					.find(".grid-heading-row .grid-row-check:checked:first")
					.prop("checked", 0);
				if (selected.length === grid.grid_pagination.page_length) {
					grid.scroll_to_top();
				}
			})
			.catch(function () {
				// before_*_remove aborted
			});
	}

	function patch_grid_prototype(GridProto) {
		if (!GridProto || !GridProto.delete_rows || GridProto.delete_rows.__logistics_ij_delete_patched) {
			return;
		}
		var orig = GridProto.delete_rows;
		GridProto.delete_rows = function () {
			if (is_internal_job_detail_grid(this)) {
				delete_selected_rows_sync(this);
				return;
			}
			return orig.apply(this, arguments);
		};
		GridProto.delete_rows.__logistics_ij_delete_patched = true;
	}

	function run() {
		if (!frappe.ui.form || !frappe.ui.form.ControlTable) {
			setTimeout(run, 50);
			return;
		}
		if (frappe.ui.form.ControlTable.prototype.make.__logistics_ij_delete_hooked) {
			return;
		}
		var orig_make = frappe.ui.form.ControlTable.prototype.make;
		frappe.ui.form.ControlTable.prototype.make = function () {
			orig_make.apply(this, arguments);
			if (this.grid) {
				patch_internal_job_detail_grid_duplicate(this.grid);
				if (this.grid.constructor && this.grid.constructor.prototype) {
					patch_grid_prototype(this.grid.constructor.prototype);
				}
			}
		};
		frappe.ui.form.ControlTable.prototype.make.__logistics_ij_delete_hooked = true;
	}
	run();
})();
