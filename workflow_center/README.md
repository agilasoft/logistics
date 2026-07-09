# Workflow Center

Unified cockpit for pending workflow actions across **all** doctypes with active workflows.

## Install

```bash
bench get-app workflow_center
bench --site <site> install-app workflow_center
```

## Features

- Lists open `Workflow Action` records for the current user's roles across every doctype (ERPNext accounting, logistics, custom).
- KPI cards: open actions, at-risk, delay risk, penalty risk, today's tasks, compliance gaps.
- Filters: company, branch, cost center, profit center, role.
- Respects Frappe `has_permission` on referenced documents.

## Route

`/app/workflow-center`
