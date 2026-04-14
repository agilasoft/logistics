// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt
//
// Frappe Grid is an ES module (export default class Grid) and is NOT exposed as
// frappe.ui.form.Grid, so patching that symbol never ran.
//
// Frappe Grid.setup_toolbar() also hides Add row / Add multiple when cannot_add_rows
// is set, then shows them again when the grid is editable (grid.js ~656–658).
//
// Patch Grid.prototype once we can resolve the class from ControlTable (first Table field).

(function patch_grid_cannot_add_rows_toolbar() {
	function apply_hide(grid) {
		if (!grid || !grid.wrapper || !grid.df) {
			return;
		}
		const cannot_add =
			grid.cannot_add_rows || (grid.df && grid.df.cannot_add_rows);
		if (cannot_add && grid.is_editable && grid.is_editable()) {
			grid.wrapper
				.find(".grid-add-row, .grid-add-multiple-rows, .grid-duplicate-rows")
				.addClass("hidden");
		}
		// Frappe setup_toolbar() also unhides .grid-upload when editable; bulk CSV import must stay off when allow_bulk_edit is false.
		if (!cint(grid.df.allow_bulk_edit)) {
			grid.wrapper.find(".grid-upload, .grid-download").addClass("hidden");
		}
	}

	/** Belt-and-suspenders after grid redraws (Frappe ~656–658 can re-show Add buttons). */
	window.logistics_hide_cannot_add_rows_buttons = function (frm, fieldname) {
		const fd = frm && frm.fields_dict && frm.fields_dict[fieldname];
		const grid = fd && fd.grid;
		if (!grid || !grid.wrapper) {
			return;
		}
		grid.wrapper
			.find(".grid-add-row, .grid-add-multiple-rows, .grid-duplicate-rows, .grid-upload, .grid-download")
			.addClass("hidden");
	};

	function patch_grid_prototype(GridProto) {
		if (!GridProto || !GridProto.setup_toolbar || GridProto.setup_toolbar.__logistics_cannot_add_rows_patched) {
			return;
		}
		const orig = GridProto.setup_toolbar;
		GridProto.setup_toolbar = function () {
			orig.apply(this, arguments);
			apply_hide(this);
		};
		GridProto.setup_toolbar.__logistics_cannot_add_rows_patched = true;
	}

	function run() {
		if (!frappe.ui.form || !frappe.ui.form.ControlTable) {
			setTimeout(run, 50);
			return;
		}
		if (frappe.ui.form.ControlTable.prototype.make.__logistics_cannot_add_rows_hooked) {
			return;
		}
		const orig_make = frappe.ui.form.ControlTable.prototype.make;
		frappe.ui.form.ControlTable.prototype.make = function () {
			orig_make.apply(this, arguments);
			if (this.grid && this.grid.constructor && this.grid.constructor.prototype) {
				const proto = this.grid.constructor.prototype;
				const already_patched = !!proto.setup_toolbar.__logistics_cannot_add_rows_patched;
				patch_grid_prototype(proto);
				// Stock setup_toolbar may have run before the patch; re-apply hide rules only.
				// Do not call setup_toolbar() here — Grid.grid_rows is not always initialized yet
				// (TypeError: can't access property "length", this.grid_rows is undefined).
				if (!already_patched && this.grid) {
					apply_hide(this.grid);
				}
			}
		};
		frappe.ui.form.ControlTable.prototype.make.__logistics_cannot_add_rows_hooked = true;
	}
	run();
})();
