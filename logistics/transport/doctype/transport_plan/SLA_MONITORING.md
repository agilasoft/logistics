# How SLA is Monitored in Transport Plan

This document describes where Service Level Agreement (SLA) data lives, how it relates to Transport Plan, and how SLA is monitored in the transport flow.

## Where SLA is Stored

SLA is tracked at **Transport Job** level, not on Transport Plan or Run Sheet.

| Field | Type | Description |
|-------|------|--------------|
| **SLA Target Date** | Datetime | When the job is due to be completed (commitment to customer). |
| **SLA Status** | Select | `On Track`, `At Risk`, `Breached`, or `Not Applicable`. |
| **SLA Notes** | Text | Free-form notes (e.g. reason for breach, mitigation). |

These fields are on the **Service Level** tab of the Transport Job form.

## Relationship: Plan → Jobs

Transport Plan does not store SLA directly. Jobs are reached via Run Sheets and Legs:

```
Transport Plan
  └── runsheets (child table: Transport Plan Run Sheets)
        └── run_sheet (Link → Run Sheet)
              └── legs (Run Sheet has child table → Transport Leg)
                    └── transport_job (Link → Transport Job)
                          └── sla_target_date, sla_status, sla_notes
```

So to see SLA for “everything in a plan” you look at all **Transport Jobs** that are linked from **Transport Legs** whose **Run Sheet** is listed in that plan’s **runsheets** table.

## How SLA is (Currently) Monitored

### Manual setting and review

- **SLA Target Date** and **SLA Status** are set and updated **manually** on each Transport Job.
- There is **no** automatic logic that:
  - Sets `sla_target_date` from template/order, or
  - Updates `sla_status` (On Track / At Risk / Breached) by comparing `sla_target_date` to current time.

So monitoring is done by:

1. **From a Transport Plan**
   - Open the plan → open each **Run Sheet** in the runsheets table → on each Run Sheet, use the **legs** table to see **Transport Job** (and open the job to see SLA fields).

2. **From Transport Job list**
   - List View / Report View on **Transport Job** with filters (e.g. Plan Date, Customer, Status) and columns **SLA Target Date**, **SLA Status**, **SLA Notes**.

3. **From Run Sheet**
   - Each Run Sheet’s legs show the linked Transport Job; open the job to view or edit SLA.

### Job status vs SLA

- **Job status** (Submitted / In Progress / Completed) is updated automatically from **Transport Leg** status when legs are saved (e.g. Assigned, Started, Completed). See `Transport Leg.update_transport_job_status()` and `Transport Job.update_status()`.
- **SLA status** is independent: it is not updated by leg status or by any scheduled task. It must be maintained manually (or by future automation).

### On Time Delivery Report

The **On Time Delivery Report** measures delivery performance (scheduled vs actual delivery, delay/early minutes, and a **service_level** percentage). That metric is **separate** from the Transport Job SLA fields above; the report does not read or write `sla_target_date` or `sla_status`.

## Summary

| Aspect | Detail |
|--------|--------|
| **SLA storage** | Transport Job: `sla_target_date`, `sla_status`, `sla_notes`. |
| **Plan → Job link** | Plan → Transport Plan Run Sheets (run_sheet) → Run Sheet → Transport Leg (transport_job) → Transport Job. |
| **SLA status updates** | Manual only; no automatic On Track / At Risk / Breached from target date. |
| **Monitoring in plan context** | Use Plan → Run Sheets → Legs → open each Transport Job and review SLA tab; or filter Transport Job list by date/run sheet and show SLA columns. |

To add automatic SLA monitoring (e.g. scheduled task that sets On Track / At Risk / Breached from `sla_target_date` and current time), new logic would need to be implemented, for example in a scheduled task that updates `sla_status` on Transport Job.
