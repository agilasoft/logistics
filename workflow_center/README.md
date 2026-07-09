# Workflow Center

Unified cockpit for pending workflow actions across **all** doctypes with active workflows.

## Deploy / upgrade on bench

If an older private `workflow_center` app is installed, replace it with this package:

```bash
cd ~/frappe-bench/apps
rm -rf workflow_center
git clone <logistics-repo> /tmp/logistics && cp -a /tmp/logistics/workflow_center workflow_center
cd workflow_center && pip install -e .
cd ~/frappe-bench
bench --site <site> install-app workflow_center
bench build --app workflow_center
bench restart
```

Verify the API resolves:

```bash
bench --site <site> execute workflow_center.api.get_workflow_center_summary
```

## Features

- Lists open `Workflow Action` records for the current user's roles across every doctype (ERPNext accounting, logistics, custom).
- KPI cards: open actions, at-risk, delay risk, penalty risk, today's tasks, compliance gaps.
- Filters: company, branch, cost center, profit center, role.
- Respects Frappe `has_permission` on referenced documents.

## Route

`/app/workflow-center`
