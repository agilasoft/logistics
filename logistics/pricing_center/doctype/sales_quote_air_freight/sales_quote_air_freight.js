// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Handle nested child table via button (similar to Web Page/Page Blocks pattern)
frappe.ui.form.on("Sales Quote", {
	refresh(frm) {
		// Add button to edit nested child table in air_freight grid
		setup_weight_break_rate_buttons(frm);
		setup_qty_break_rate_buttons(frm);
		// Refresh weight break HTML fields for all rows
		refresh_all_weight_break_html(frm);
		refresh_all_qty_break_html(frm);
	},
	
	air_freight: function(frm) {
		// Re-setup buttons when air_freight table changes
		setup_weight_break_rate_buttons(frm);
		setup_qty_break_rate_buttons(frm);
	}
});

// Child table events for Sales Quote Air Freight
frappe.ui.form.on('Sales Quote Air Freight', {
	form_render: function(frm, cdt, cdn) {
		// Refresh weight break HTML when row is rendered
		refresh_weight_break_html_for_row(frm, cdt, cdn);
		refresh_qty_break_html_for_row(frm, cdt, cdn);
	},
	
	air_freight_add: function(frm, cdt, cdn) {
		// Initialize HTML fields for new row
		refresh_weight_break_html_for_row(frm, cdt, cdn);
		refresh_qty_break_html_for_row(frm, cdt, cdn);
	}
});

/**
 * Setup buttons for editing nested Weight Break Rate table
 * Similar to how Web Page/Page Blocks implement nested child tables
 */
function setup_weight_break_rate_buttons(frm) {
	if (!frm.fields_dict.air_freight || !frm.fields_dict.air_freight.grid) {
		return;
	}
	
	const grid = frm.fields_dict.air_freight.grid;
	
	// Function to add button to a grid row
	function add_button_to_row(grid_row) {
		if (!grid_row || !grid_row.doc) return;
		
		// Check if button already added
		if (grid_row.doc.__weight_break_button_added) return;
		grid_row.doc.__weight_break_button_added = true;
		
		// Find or create actions container
		const $row = $(grid_row.wrapper || grid_row.$wrapper);
		let $actions = $row.find('.grid-row-actions, .row-actions');
		
		if ($actions.length === 0) {
			// Try to find the row content area
			const $rowContent = $row.find('.grid-row-content, .row-content, .list-row-content');
			if ($rowContent.length > 0) {
				$actions = $('<div class="grid-row-actions" style="display: inline-block; margin-left: 10px;"></div>');
				$rowContent.append($actions);
			} else {
				// Fallback: append to row
				$actions = $('<div class="grid-row-actions" style="display: inline-block; margin-left: 10px;"></div>');
				$row.append($actions);
			}
		}
		
		// Remove existing button if any
		$actions.find('.edit-weight-break-rate').remove();
		
		// Add "Edit Weight Break Rate" button
		const $btn = $(`
			<button class="btn btn-xs btn-default edit-weight-break-rate" 
					title="${__('Edit Weight Break Rate')}"
					type="button">
				<i class="fa fa-table"></i> ${__('Weight Break')}
			</button>
		`);
		
		$btn.on('click', function(e) {
			e.stopPropagation();
			e.preventDefault();
			open_weight_break_rate_dialog(frm, grid_row.doc);
		});
		
		$actions.append($btn);
	}
	
	// Add buttons to existing rows
	if (grid.grid_rows) {
		grid.grid_rows.forEach((grid_row) => {
			add_button_to_row(grid_row);
		});
	}
	
	// Listen for new rows being added
	grid.wrapper.off('add.weight_break').on('add.weight_break', function() {
		setTimeout(() => {
			if (grid.grid_rows) {
				grid.grid_rows.forEach((grid_row) => {
					add_button_to_row(grid_row);
				});
			}
		}, 200);
	});
	
	// Listen for grid refresh
	grid.wrapper.off('refresh.weight_break').on('refresh.weight_break', function() {
		setTimeout(() => {
			if (grid.grid_rows) {
				grid.grid_rows.forEach((grid_row) => {
					// Reset flag to allow re-adding button
					if (grid_row.doc) {
						grid_row.doc.__weight_break_button_added = false;
					}
					add_button_to_row(grid_row);
				});
			}
		}, 200);
	});
}

/**
 * Open dialog to edit Weight Break records for Sales Quote Air Freight
 * This manages Sales Quote Weight Break records linked to the air freight line
 */
function open_weight_break_rate_dialog(parent_frm, parent_row) {
	const row_name = parent_row.name;
	const row_idx = parent_row.idx;
	
	// Check if row is saved
	if (!row_name || row_name === 'new') {
		frappe.msgprint({
			title: __('Save Required'),
			message: __('Please save the Sales Quote first before adding weight breaks.'),
			indicator: 'orange'
		});
		return;
	}
	
	// Load existing weight break records
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Sales Quote Weight Break',
			filters: {
				reference_doctype: 'Sales Quote Air Freight',
				reference_no: row_name
			},
			fields: ['name', 'type', 'rate_type', 'weight_break', 'unit_rate'],
			order_by: 'type, weight_break'
		},
		callback: function(r) {
			const existing_records = r.message || [];
			show_weight_break_dialog(parent_frm, parent_row, row_name, row_idx, existing_records);
		}
	});
}

/**
 * Show the weight break dialog with existing data
 */
function show_weight_break_dialog(parent_frm, parent_row, row_name, row_idx, existing_records) {
	// Separate selling and cost records
	const selling_records = existing_records.filter(r => r.type === 'Selling');
	const cost_records = existing_records.filter(r => r.type === 'Cost');
	
	// Create dialog with two tables - one for Selling and one for Cost
	const dialog = new frappe.ui.Dialog({
		title: __("Weight Break Rates") + (row_idx ? ` - ${__('Row')} ${row_idx}` : ''),
		size: 'large',
		fields: [
			{
				fieldtype: "HTML",
				options: `<div class="alert alert-info" style="margin-bottom: 15px;">
					<i class="fa fa-info-circle"></i> 
					${__("Define weight break rates for selling and cost calculations.")}
				</div>`
			},
			{
				fieldtype: "Section Break",
				label: __("Selling Weight Breaks")
			},
			{
				fieldname: "selling_weight_breaks",
				fieldtype: "Table",
				label: __("Selling Weight Breaks"),
				cannot_add_rows: false,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: selling_records.map(r => ({
					rate_type: r.rate_type,
					weight_break: r.weight_break,
					unit_rate: r.unit_rate
				})),
				fields: [
					{
						fieldname: "rate_type",
						fieldtype: "Select",
						label: __("Rate Type"),
						options: "Normal\nMinimum\nWeight Break",
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "weight_break",
						fieldtype: "Float",
						label: __("Weight Break"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "unit_rate",
						fieldtype: "Currency",
						label: __("Unit Rate"),
						in_list_view: 1,
						reqd: 1
					}
				]
			},
			{
				fieldtype: "Section Break",
				label: __("Cost Weight Breaks")
			},
			{
				fieldname: "cost_weight_breaks",
				fieldtype: "Table",
				label: __("Cost Weight Breaks"),
				cannot_add_rows: false,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: cost_records.map(r => ({
					rate_type: r.rate_type,
					weight_break: r.weight_break,
					unit_rate: r.unit_rate
				})),
				fields: [
					{
						fieldname: "rate_type",
						fieldtype: "Select",
						label: __("Rate Type"),
						options: "Normal\nMinimum\nWeight Break",
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "weight_break",
						fieldtype: "Float",
						label: __("Weight Break"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "unit_rate",
						fieldtype: "Currency",
						label: __("Unit Rate"),
						in_list_view: 1,
						reqd: 1
					}
				]
			}
		],
		primary_action_label: __("Save"),
		primary_action: async function(values) {
			try {
				// Save both selling and cost weight breaks
				await save_weight_breaks(parent_frm, row_name, values.selling_weight_breaks || [], 'Selling');
				await save_weight_breaks(parent_frm, row_name, values.cost_weight_breaks || [], 'Cost');
				
				// Refresh the HTML fields
				await refresh_weight_break_html_fields(parent_frm, row_name);
			
			dialog.hide();
			frappe.show_alert({
					message: __("Weight Break Rates saved successfully"),
				indicator: "green"
			});
			} catch (error) {
				frappe.msgprint({
					title: __('Error'),
					message: error.toString(),
					indicator: 'red'
				});
			}
		}
	});
	
	dialog.show();
}

/**
 * Save weight break records to database
 */
function save_weight_breaks(parent_frm, air_freight_name, weight_breaks, record_type) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'logistics.logistics_sales.doctype.sales_quote_weight_break.sales_quote_weight_break.save_weight_breaks_for_air_freight',
			args: {
				air_freight_name: air_freight_name,
				weight_breaks: weight_breaks,
				record_type: record_type
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					resolve(r.message);
				} else {
					reject(r.message ? r.message.error : 'Failed to save weight breaks');
				}
			},
			error: function(err) {
				reject(err);
			}
		});
	});
}

/**
 * Refresh weight break HTML fields for a specific row
 */
function refresh_weight_break_html_for_row(frm, cdt, cdn) {
	if (!cdn || cdn === 'new') {
		return;
	}
	
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	
	// Refresh selling weight break HTML
	frappe.call({
		method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.get_weight_break_html',
		args: {
			air_freight_name: cdn,
			record_type: 'Selling'
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, 'selling_weight_break', r.message.html);
			}
		}
	});
	
	// Refresh cost weight break HTML
	frappe.call({
		method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.get_weight_break_html',
		args: {
			air_freight_name: cdn,
			record_type: 'Cost'
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, 'cost_weight_break', r.message.html);
			}
		}
	});
}

/**
 * Refresh weight break HTML fields for all rows in the air_freight table
 */
function refresh_all_weight_break_html(frm) {
	if (!frm.doc.air_freight || !frm.doc.air_freight.length) {
		return;
	}
	
	frm.doc.air_freight.forEach(function(row) {
		if (row.name && row.name !== 'new') {
			refresh_weight_break_html_for_row(frm, row.doctype, row.name);
		}
	});
}

/**
 * Refresh weight break HTML fields by calling server method
 */
function refresh_weight_break_html_fields(parent_frm, air_freight_name) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.refresh_weight_break_html_fields',
			args: {
				air_freight_name: air_freight_name
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					// Update the local document with the new HTML
					const row = frappe.get_doc('Sales Quote Air Freight', air_freight_name);
					if (row) {
						row.selling_weight_break = r.message.selling_html;
						row.cost_weight_break = r.message.cost_html;
					}
					
					// Refresh the parent form
					parent_frm.refresh_field('air_freight');
					
					resolve(r.message);
				} else {
					reject(r.message ? r.message.error : 'Failed to refresh HTML fields');
				}
			},
			error: function(err) {
				reject(err);
			}
		});
	});
}

/**
 * Setup buttons for editing nested Qty Break Rate table
 * Similar to weight break implementation
 */
function setup_qty_break_rate_buttons(frm) {
	if (!frm.fields_dict.air_freight || !frm.fields_dict.air_freight.grid) {
		return;
	}
	
	const grid = frm.fields_dict.air_freight.grid;
	
	// Function to add button to a grid row
	function add_button_to_row(grid_row) {
		if (!grid_row || !grid_row.doc) return;
		
		// Check if button already added
		if (grid_row.doc.__qty_break_button_added) return;
		grid_row.doc.__qty_break_button_added = true;
		
		// Find or create actions container
		const $row = $(grid_row.wrapper || grid_row.$wrapper);
		let $actions = $row.find('.grid-row-actions, .row-actions');
		
		if ($actions.length === 0) {
			// Try to find the row content area
			const $rowContent = $row.find('.grid-row-content, .row-content, .list-row-content');
			if ($rowContent.length > 0) {
				$actions = $('<div class="grid-row-actions" style="display: inline-block; margin-left: 10px;"></div>');
				$rowContent.append($actions);
			} else {
				// Fallback: append to row
				$actions = $('<div class="grid-row-actions" style="display: inline-block; margin-left: 10px;"></div>');
				$row.append($actions);
			}
		}
		
		// Remove existing button if any
		$actions.find('.edit-qty-break-rate').remove();
		
		// Add "Edit Qty Break Rate" button
		const $btn = $(`
			<button class="btn btn-xs btn-default edit-qty-break-rate" 
					title="${__('Edit Qty Break Rate')}"
					type="button">
				<i class="fa fa-cubes"></i> ${__('Qty Break')}
			</button>
		`);
		
		$btn.on('click', function(e) {
			e.stopPropagation();
			e.preventDefault();
			open_qty_break_rate_dialog(frm, grid_row.doc);
		});
		
		$actions.append($btn);
	}
	
	// Add buttons to existing rows
	if (grid.grid_rows) {
		grid.grid_rows.forEach((grid_row) => {
			add_button_to_row(grid_row);
		});
	}
	
	// Listen for new rows being added
	grid.wrapper.off('add.qty_break').on('add.qty_break', function() {
		setTimeout(() => {
			if (grid.grid_rows) {
				grid.grid_rows.forEach((grid_row) => {
					add_button_to_row(grid_row);
				});
			}
		}, 200);
	});
	
	// Listen for grid refresh
	grid.wrapper.off('refresh.qty_break').on('refresh.qty_break', function() {
		setTimeout(() => {
			if (grid.grid_rows) {
				grid.grid_rows.forEach((grid_row) => {
					// Reset flag to allow re-adding button
					if (grid_row.doc) {
						grid_row.doc.__qty_break_button_added = false;
					}
					add_button_to_row(grid_row);
				});
			}
		}, 200);
	});
}

/**
 * Open dialog to edit Qty Break records for Sales Quote Air Freight
 * This manages Sales Quote Qty Break records linked to the air freight line
 */
function open_qty_break_rate_dialog(parent_frm, parent_row) {
	const row_name = parent_row.name;
	const row_idx = parent_row.idx;
	
	// Check if row is saved
	if (!row_name || row_name === 'new') {
		frappe.msgprint({
			title: __('Save Required'),
			message: __('Please save the Sales Quote first before adding qty breaks.'),
			indicator: 'orange'
		});
		return;
	}
	
	// Load existing qty break records
	frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Sales Quote Qty Break',
			filters: {
				reference_doctype: 'Sales Quote Air Freight',
				reference_no: row_name
			},
			fields: ['name', 'type', 'rate_type', 'qty_break', 'unit_rate', 'currency'],
			order_by: 'type, qty_break'
		},
		callback: function(r) {
			const existing_records = r.message || [];
			show_qty_break_dialog(parent_frm, parent_row, row_name, row_idx, existing_records);
		}
	});
}

/**
 * Show the qty break dialog with existing data
 */
function show_qty_break_dialog(parent_frm, parent_row, row_name, row_idx, existing_records) {
	// Separate selling and cost records
	const selling_records = existing_records.filter(r => r.type === 'Selling');
	const cost_records = existing_records.filter(r => r.type === 'Cost');
	
	// Get currency from parent row
	const currency = parent_row.currency || 'USD';
	
	// Create dialog with two tables - one for Selling and one for Cost
	const dialog = new frappe.ui.Dialog({
		title: __("Qty Break Rates") + (row_idx ? ` - ${__('Row')} ${row_idx}` : ''),
		size: 'large',
		fields: [
			{
				fieldtype: "HTML",
				options: `<div class="alert alert-info" style="margin-bottom: 15px;">
					<i class="fa fa-info-circle"></i> 
					${__("Define quantity break rates for selling and cost calculations based on package/quantity count.")}
				</div>`
			},
			{
				fieldtype: "Section Break",
				label: __("Selling Qty Breaks")
			},
			{
				fieldname: "selling_qty_breaks",
				fieldtype: "Table",
				label: __("Selling Qty Breaks"),
				cannot_add_rows: false,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: selling_records.map(r => ({
					rate_type: r.rate_type,
					qty_break: r.qty_break,
					unit_rate: r.unit_rate,
					currency: r.currency || currency
				})),
				fields: [
					{
						fieldname: "rate_type",
						fieldtype: "Select",
						label: __("Rate Type"),
						options: "Normal\nMinimum\nQty Break",
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "qty_break",
						fieldtype: "Float",
						label: __("Qty Break"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "unit_rate",
						fieldtype: "Currency",
						label: __("Unit Rate"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "currency",
						fieldtype: "Link",
						label: __("Currency"),
						options: "Currency",
						default: currency,
						in_list_view: 1
					}
				]
			},
			{
				fieldtype: "Section Break",
				label: __("Cost Qty Breaks")
			},
			{
				fieldname: "cost_qty_breaks",
				fieldtype: "Table",
				label: __("Cost Qty Breaks"),
				cannot_add_rows: false,
				cannot_delete_rows: false,
				in_place_edit: true,
				data: cost_records.map(r => ({
					rate_type: r.rate_type,
					qty_break: r.qty_break,
					unit_rate: r.unit_rate,
					currency: r.currency || currency
				})),
				fields: [
					{
						fieldname: "rate_type",
						fieldtype: "Select",
						label: __("Rate Type"),
						options: "Normal\nMinimum\nQty Break",
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "qty_break",
						fieldtype: "Float",
						label: __("Qty Break"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "unit_rate",
						fieldtype: "Currency",
						label: __("Unit Rate"),
						in_list_view: 1,
						reqd: 1
					},
					{
						fieldname: "currency",
						fieldtype: "Link",
						label: __("Currency"),
						options: "Currency",
						default: currency,
						in_list_view: 1
					}
				]
			}
		],
		primary_action_label: __("Save"),
		primary_action: async function(values) {
			try {
				// Save both selling and cost qty breaks
				await save_qty_breaks(parent_frm, row_name, values.selling_qty_breaks || [], 'Selling');
				await save_qty_breaks(parent_frm, row_name, values.cost_qty_breaks || [], 'Cost');
				
				// Refresh the HTML fields
				await refresh_qty_break_html_fields(parent_frm, row_name);
			
			dialog.hide();
			frappe.show_alert({
					message: __("Qty Break Rates saved successfully"),
				indicator: "green"
			});
			} catch (error) {
				frappe.msgprint({
					title: __('Error'),
					message: error.toString(),
					indicator: 'red'
				});
			}
		}
	});
	
	dialog.show();
}

/**
 * Save qty break records to database
 */
function save_qty_breaks(parent_frm, air_freight_name, qty_breaks, record_type) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'logistics.logistics_sales.doctype.sales_quote_qty_break.sales_quote_qty_break.save_qty_breaks_for_air_freight',
			args: {
				air_freight_name: air_freight_name,
				qty_breaks: qty_breaks,
				record_type: record_type
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					resolve(r.message);
				} else {
					reject(r.message ? r.message.error : 'Failed to save qty breaks');
				}
			},
			error: function(err) {
				reject(err);
			}
		});
	});
}

/**
 * Refresh qty break HTML fields for a specific row
 */
function refresh_qty_break_html_for_row(frm, cdt, cdn) {
	if (!cdn || cdn === 'new') {
		return;
	}
	
	const row = locals[cdt] && locals[cdt][cdn];
	if (!row) {
		return;
	}
	
	// Refresh selling qty break HTML
	frappe.call({
		method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.get_qty_break_html',
		args: {
			air_freight_name: cdn,
			record_type: 'Selling'
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, 'selling_qty_break', r.message.html);
			}
		}
	});
	
	// Refresh cost qty break HTML
	frappe.call({
		method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.get_qty_break_html',
		args: {
			air_freight_name: cdn,
			record_type: 'Cost'
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.model.set_value(cdt, cdn, 'cost_qty_break', r.message.html);
			}
		}
	});
}

/**
 * Refresh qty break HTML fields for all rows in the air_freight table
 */
function refresh_all_qty_break_html(frm) {
	if (!frm.doc.air_freight || !frm.doc.air_freight.length) {
		return;
	}
	
	frm.doc.air_freight.forEach(function(row) {
		if (row.name && row.name !== 'new') {
			refresh_qty_break_html_for_row(frm, row.doctype, row.name);
		}
	});
}

/**
 * Refresh qty break HTML fields by calling server method
 */
function refresh_qty_break_html_fields(parent_frm, air_freight_name) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method: 'logistics.pricing_center.doctype.sales_quote_air_freight.sales_quote_air_freight.refresh_qty_break_html_fields',
			args: {
				air_freight_name: air_freight_name
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					// Update the local document with the new HTML
					const row = frappe.get_doc('Sales Quote Air Freight', air_freight_name);
					if (row) {
						row.selling_qty_break = r.message.selling_html;
						row.cost_qty_break = r.message.cost_html;
					}
					
					// Refresh the parent form
					parent_frm.refresh_field('air_freight');
					
					resolve(r.message);
				} else {
					reject(r.message ? r.message.error : 'Failed to refresh HTML fields');
				}
			},
			error: function(err) {
				reject(err);
			}
		});
	});
}
