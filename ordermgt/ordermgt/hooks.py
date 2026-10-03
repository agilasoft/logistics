app_name = "ordermgt"
app_title = "Order Management"
app_publisher = "Agilasoft Cloud Technologies Inc."
app_description = "Marketplace order, listing, and stock sync for CargoNext warehouses"
app_email = "info@agilasoft.com"
app_license = "AGPL-3.0-or-later"

required_apps = ["erpnext", "logistics"]

fixtures = ["role.json"]

doc_events = {
	"Warehouse Job": {
		"on_submit": "ordermgt.order_management.tasks.on_warehouse_job_submit",
	},
}

scheduler_events = {
	"cron": {
		"*/10 * * * *": [
			"ordermgt.order_management.tasks.pull_orders",
		],
	},
	"hourly": [
		"ordermgt.order_management.tasks.push_stock",
	],
	"daily": [
		"ordermgt.order_management.tasks.cleanup_sync_logs",
	],
}
