# Air Freight Workspace Layout

This document provides a comprehensive layout guide for configuring the Air Freight workspace in the Frappe frontend.

## Workspace Structure

### 1. Onboarding Block
- **Type**: Onboarding
- **Name**: "Air Freight"
- **Purpose**: Guide new users through initial setup

---

### 2. Quick Access - Process Flow Section

**Header**: "Quick Access - Process Flow"

**Shortcuts** (arranged in a row, 3 columns each):

1. **Air Shipment**
   - Type: DocType
   - Link To: "Air Shipment"
   - Color: Blue
   - Doc View: List
   - Stats Filter: [] (empty)

2. **Air Consolidation**
   - Type: DocType
   - Link To: "Air Consolidation"
   - Color: Orange
   - Doc View: List
   - Stats Filter: [] (empty)

3. **Master Air Waybill**
   - Type: DocType
   - Link To: "Master Air Waybill"
   - Color: Grey
   - Doc View: List
   - Stats Filter: [] (empty)

4. **Sales Quote**
   - Type: DocType
   - Link To: "Sales Quote"
   - Color: Grey
   - Doc View: List
   - Stats Filter: [] (empty)

5. **Airlines**
   - Type: DocType
   - Link To: "Airline"
   - Color: Grey
   - Doc View: List
   - Stats Filter: [] (empty)

6. **Airports**
   - Type: DocType
   - Link To: "UNLOCO"
   - Color: Grey
   - Doc View: List
   - Stats Filter: [] (empty)

---

### 3. Settings & Configuration Card

**Card Break**: "Settings & Configuration"

**Links**:

1. **IATA Settings**
   - Type: Link
   - Link Type: DocType
   - Link To: "IATA Settings"
   - Is Query Report: No

2. **Air Freight Rate**
   - Type: Link
   - Link Type: DocType
   - Link To: "Air Freight Rate"
   - Is Query Report: No

3. **ULD Types**
   - Type: Link
   - Link Type: DocType
   - Link To: "Unit Load Device"
   - Is Query Report: No

4. **Flight Schedule Settings**
   - Type: Link
   - Link Type: DocType
   - Link To: "Flight Schedule Settings"
   - Is Query Report: No

5. **IATA Message Queue**
   - Type: Link
   - Link Type: DocType
   - Link To: "IATA Message Queue"
   - Is Query Report: No

---

### 4. Master Data Card

**Card Break**: "Master Data"

**Links**:

1. **Airline**
   - Type: Link
   - Link Type: DocType
   - Link To: "Airline"
   - Is Query Report: No

2. **Airline Master**
   - Type: Link
   - Link Type: DocType
   - Link To: "Airline Master"
   - Is Query Report: No

3. **Airline Membership**
   - Type: Link
   - Link Type: DocType
   - Link To: "Airline Membership"
   - Is Query Report: No

4. **Airport Master**
   - Type: Link
   - Link Type: DocType
   - Link To: "Airport Master"
   - Is Query Report: No

5. **UNLOCO** (Ports/Airports)
   - Type: Link
   - Link Type: DocType
   - Link To: "UNLOCO"
   - Is Query Report: No

6. **Unit Load Device**
   - Type: Link
   - Link Type: DocType
   - Link To: "Unit Load Device"
   - Is Query Report: No

7. **Master Air Waybill**
   - Type: Link
   - Link Type: DocType
   - Link To: "Master Air Waybill"
   - Is Query Report: No

8. **Flight Schedule**
   - Type: Link
   - Link Type: DocType
   - Link To: "Flight Schedule"
   - Is Query Report: No

9. **Flight Route**
   - Type: Link
   - Link Type: DocType
   - Link To: "Flight Route"
   - Is Query Report: No

10. **Dangerous Goods Declaration**
    - Type: Link
    - Link Type: DocType
    - Link To: "Dangerous Goods Declaration"
    - Is Query Report: No

11. **Job Milestone**
    - Type: Link
    - Link Type: DocType
    - Link To: "Job Milestone"
    - Is Query Report: No

---

### 5. Operational Documents Card

**Card Break**: "Operational Documents"

**Links**:

1. **Air Shipment**
   - Type: Link
   - Link Type: DocType
   - Link To: "Air Shipment"
   - Is Query Report: No

2. **Air Consolidation**
   - Type: Link
   - Link Type: DocType
   - Link To: "Air Consolidation"
   - Is Query Report: No

3. **Sales Quote**
   - Type: Link
   - Link Type: DocType
   - Link To: "Sales Quote"
   - Is Query Report: No

---

### 6. Operational Reports Card

**Card Break**: "Operational Reports"

**Links**:

1. **Air Shipment Status Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Air Shipment Status Report"
   - Is Query Report: Yes

2. **Air Consolidation Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Air Consolidation Report"
   - Is Query Report: Yes

3. **On-Time Performance Report**
   - Type: Link
   - Link Type: Report
   - Link To: "On-Time Performance Report"
   - Is Query Report: Yes

4. **Dangerous Goods Compliance Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Dangerous Goods Compliance Report"
   - Is Query Report: Yes

---

### 7. Financial Reports Card

**Card Break**: "Financial Reports"

**Links**:

1. **Air Freight Revenue Analysis**
   - Type: Link
   - Link Type: Report
   - Link To: "Air Freight Revenue Analysis"
   - Is Query Report: Yes

2. **Air Freight Cost Analysis**
   - Type: Link
   - Link Type: Report
   - Link To: "Air Freight Cost Analysis"
   - Is Query Report: Yes

3. **Billing Status Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Billing Status Report"
   - Is Query Report: Yes

---

### 8. Analytics & Insights Card

**Card Break**: "Analytics & Insights"

**Links**:

1. **Air Freight Performance Dashboard**
   - Type: Link
   - Link Type: Report
   - Link To: "Air Freight Performance Dashboard"
   - Is Query Report: Yes

2. **Route Analysis Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Route Analysis Report"
   - Is Query Report: Yes

3. **Airline Performance Report**
   - Type: Link
   - Link Type: Report
   - Link To: "Airline Performance Report"
   - Is Query Report: Yes

---

## Number Cards (Optional)

If you want to add number cards to the workspace, you can create them in the frontend with the following suggested cards:

1. **Open Air Shipments**
   - Document Type: Air Shipment
   - Function: Count
   - Filters: `[["docstatus", "=", 0]]`

2. **Pending Consolidations**
   - Document Type: Air Consolidation
   - Function: Count
   - Filters: `[["docstatus", "=", 0]]`

3. **Unbilled Shipments**
   - Document Type: Air Shipment
   - Function: Count
   - Filters: `[["billing_status", "in", ["Not Billed", "Pending", "Partially Billed"]]]`

4. **On-Time Shipments (This Month)**
   - Document Type: Air Shipment
   - Function: Count
   - Filters: `[["eta", ">=", frappe.datetime.month_start()], ["eta", "<=", frappe.datetime.month_end()], ["on_time_status", "=", "On Time"]]`

---

## Content Block Structure

The content block should be structured as follows (in order):

1. **Onboarding Block** (col: 12)
2. **Spacer** (col: 12)
3. **Header**: "Quick Access - Process Flow" (col: 12)
4. **Shortcuts**: 6 shortcuts in 2 rows (3 columns each)
5. **Spacer** (col: 12)
6. **Header**: "Settings & Configuration" (col: 12)
7. **Shortcuts**: Settings shortcuts (3-4 columns)
8. **Spacer** (col: 12)

---

## Notes

- All `stats_filter` fields should be empty arrays: `[]`
- All shortcuts should use `doc_view: "List"`
- Card Breaks are used to group related links together
- Reports should have `is_query_report: true`
- DocTypes should have `is_query_report: false`
- The workspace should be public and accessible to Air Freight Manager and Air Freight Agent roles

---

## Color Scheme Suggestions

- **Primary Operations**: Blue (Air Shipment)
- **Secondary Operations**: Orange (Air Consolidation)
- **Master Data**: Grey
- **Settings**: Grey
- **Reports**: Default (no specific color needed)

---

## Workspace Properties

- **Title**: "Air Freight"
- **Label**: "Air Freight"
- **Icon**: "sidebar-expand" (or choose an appropriate icon)
- **Public**: Yes
- **Module**: "Air Freight"
- **Indicator Color**: Green
