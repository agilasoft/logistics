# Air Freight Workspace Layout

## Basic Information
- **Title**: Air Freight
- **Label**: Air Freight
- **Module**: Air Freight
- **Icon**: sidebar-expand
- **Indicator Color**: green
- **Public**: Yes

---

## Shortcuts (8 total)

### 1. Air Shipment
- **Label**: Air Shipment
- **Link To**: Air Shipment
- **Type**: DocType
- **Color**: Blue
- **Doc View**: List
- **Stats Filter**: `[]` (empty - IMPORTANT: Do not add status filter)

### 2. Air Consolidation
- **Label**: Air Consolidation
- **Link To**: Air Consolidation
- **Type**: DocType
- **Color**: Orange
- **Doc View**: List
- **Stats Filter**: `[]` (empty - IMPORTANT: Do not add status filter)

### 3. Master Air Waybill
- **Label**: Master Air Waybill
- **Link To**: Master Air Waybill
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

### 4. Sales Quote
- **Label**: Sales Quote
- **Link To**: Sales Quote
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

### 5. Airlines
- **Label**: Airlines
- **Link To**: Airline
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

### 6. Airports
- **Label**: Airports
- **Link To**: Location
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

### 7. ULD Types
- **Label**: ULD Types
- **Link To**: Unit Load Device
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

### 8. IATA Settings
- **Label**: IATA Settings
- **Link To**: IATA Settings
- **Type**: DocType
- **Color**: Grey
- **Doc View**: List
- **Stats Filter**: `[]`

---

## Content Blocks

### Block 1: Onboarding
- **Type**: Onboarding
- **Onboarding Name**: Air Freight
- **Column**: 12

### Block 2: Spacer
- **Type**: Spacer
- **Column**: 12

### Block 3: Header - Quick Access
- **Type**: Header
- **Text**: `<span class="h4"><b>Quick Access - Process Flow</b></span>`
- **Column**: 12

### Block 4-9: Quick Access Shortcuts (6 shortcuts, 3 columns each)
1. **Air Shipment** (Column: 3)
2. **Air Consolidation** (Column: 3)
3. **Master Air Waybill** (Column: 3)
4. **Sales Quote** (Column: 3)
5. **Airlines** (Column: 3)
6. **Airports** (Column: 3)

### Block 10: Spacer
- **Type**: Spacer
- **Column**: 12

### Block 11: Header - Settings
- **Type**: Header
- **Text**: `<span class="h4"><b>Settings & Configuration</b></span>`
- **Column**: 12

### Block 12-14: Settings Shortcuts (3 shortcuts, 4 columns each)
1. **IATA Settings** (Column: 4)
2. **Air Freight Rate** (Column: 4)
3. **ULD Types** (Column: 4)

---

## Links (Sidebar) - 23 total

### Section 1: Settings & Configuration (Card Break)
- **Type**: Card Break
- **Label**: Settings & Configuration
- **Link Count**: 2

#### Links:
1. **IATA Settings**
   - Type: Link
   - Link Type: DocType
   - Link To: IATA Settings
   - Is Query Report: No

2. **Air Freight Rate**
   - Type: Link
   - Link Type: DocType
   - Link To: Air Freight Rate
   - Is Query Report: No

---

### Section 2: Master Data (Card Break)
- **Type**: Card Break
- **Label**: Master Data
- **Link Count**: 6

#### Links:
1. **Airline**
   - Type: Link
   - Link Type: DocType
   - Link To: Airline
   - Is Query Report: No

2. **Unit Load Device**
   - Type: Link
   - Link Type: DocType
   - Link To: Unit Load Device
   - Is Query Report: No

3. **Master Air Waybill**
   - Type: Link
   - Link Type: DocType
   - Link To: Master Air Waybill
   - Is Query Report: No

4. **Flight Schedule**
   - Type: Link
   - Link Type: DocType
   - Link To: Flight Schedule
   - Is Query Report: No

5. **Flight Route**
   - Type: Link
   - Link Type: DocType
   - Link To: Flight Route
   - Is Query Report: No

6. **Dangerous Goods Declaration**
   - Type: Link
   - Link Type: DocType
   - Link To: Dangerous Goods Declaration
   - Is Query Report: No

---

### Section 3: Operational Reports (Card Break)
- **Type**: Card Break
- **Label**: Operational Reports
- **Link Count**: 4

#### Links:
1. **Air Shipment Status Report**
   - Type: Link
   - Link Type: Report
   - Link To: Air Shipment Status Report
   - Is Query Report: Yes

2. **Air Consolidation Report**
   - Type: Link
   - Link Type: Report
   - Link To: Air Consolidation Report
   - Is Query Report: Yes

3. **On-Time Performance Report**
   - Type: Link
   - Link Type: Report
   - Link To: On-Time Performance Report
   - Is Query Report: Yes

4. **Dangerous Goods Compliance Report**
   - Type: Link
   - Link Type: Report
   - Link To: Dangerous Goods Compliance Report
   - Is Query Report: Yes

---

### Section 4: Financial Reports (Card Break)
- **Type**: Card Break
- **Label**: Financial Reports
- **Link Count**: 3

#### Links:
1. **Air Freight Revenue Analysis**
   - Type: Link
   - Link Type: Report
   - Link To: Air Freight Revenue Analysis
   - Is Query Report: Yes

2. **Air Freight Cost Analysis**
   - Type: Link
   - Link Type: Report
   - Link To: Air Freight Cost Analysis
   - Is Query Report: Yes

3. **Billing Status Report**
   - Type: Link
   - Link Type: Report
   - Link To: Billing Status Report
   - Is Query Report: Yes

---

### Section 5: Analytics & Insights (Card Break)
- **Type**: Card Break
- **Label**: Analytics & Insights
- **Link Count**: 3

#### Links:
1. **Air Freight Performance Dashboard**
   - Type: Link
   - Link Type: Report
   - Link To: Air Freight Performance Dashboard
   - Is Query Report: Yes

2. **Route Analysis Report**
   - Type: Link
   - Link Type: Report
   - Link To: Route Analysis Report
   - Is Query Report: Yes

3. **Airline Performance Report**
   - Type: Link
   - Link Type: Report
   - Link To: Airline Performance Report
   - Is Query Report: Yes

---

## Important Notes

### ⚠️ CRITICAL: Stats Filter Configuration
- **DO NOT** add any `status` field filters to shortcuts
- All shortcuts must have `stats_filter` set to `[]` (empty array)
- The `status` field does not exist in Air Shipment or Air Consolidation doctypes
- Adding status filters will cause errors: "Field not permitted in query: status"

### Number Cards
- Leave `number_cards` empty: `[]`
- Do not create number card doctypes for this workspace

### Charts
- Optional: Profit and Loss chart can be added if needed

---

## Configuration Steps (Frontend)

1. **Open Workspace**: Go to Workspace List → Open "Air Freight"

2. **Configure Shortcuts**:
   - Add 8 shortcuts as listed above
   - Set all `stats_filter` to empty `[]`
   - Set appropriate colors and labels

3. **Configure Content Blocks**:
   - Add Onboarding block (Air Freight)
   - Add Headers for sections
   - Add Shortcuts in content area
   - Use appropriate column widths (3, 4, or 12)

4. **Configure Links (Sidebar)**:
   - Add Card Breaks for each section
   - Add Links under each section
   - Mark Reports with "Is Query Report: Yes"
   - Mark DocTypes with "Is Query Report: No"

5. **Save and Test**:
   - Save the workspace
   - Clear browser cache
   - Test the workspace to ensure no errors

---

## Summary

- **8 Shortcuts** (all with empty stats_filter)
- **14 Content Blocks** (onboarding, headers, spacers, shortcuts)
- **23 Links** organized in 5 sections:
  - Settings & Configuration (2 links)
  - Master Data (6 links)
  - Operational Reports (4 links)
  - Financial Reports (3 links)
  - Analytics & Insights (3 links)


