app_name = "workflow_center"
app_title = "Workflow Center"
app_publisher = "Agilasoft Cloud Technologies Inc."
app_description = "Unified cockpit for pending workflow actions across all doctypes"
app_email = "info@agilasoft.com"
app_license = "AGPL-3.0-or-later"

app_include_css = ["/assets/workflow_center/css/workflow_center.css"]

after_install = "workflow_center.install.after_install"

add_to_apps_screen = [
	{
		"name": "workflow_center",
		"logo": "/assets/workflow_center/images/workflow_center.svg",
		"title": "Workflow Center",
		"route": "/workflow-center",
		"has_permission": "workflow_center.workflow_center.api.has_app_permission",
	}
]
