// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Measurements (dimension/volume/weight/chargeable) are read-only and
// always fetched from Warehouse Item via fetch_from. Do not recalculate
// or overwrite UOMs from Warehouse Settings here.

frappe.ui.form.on('Stocktake Order Item', {
});
