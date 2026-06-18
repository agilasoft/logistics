# MICE Module

**MICE** (Meetings, Incentives, Conferences and Exhibitions) manages trade-show, conference, and event programmes across four lifecycle stages: **Pre-Show**, **Logistics**, **On-Site**, and **Post-Show**. Each programme links to an ERPNext **Project**, supports multimodal operational jobs, charges, milestones, and documents—aligned with the Special Projects pattern.

Go to **Home > MICE** to open the workspace.

## Key concepts

### MICE Project

The main programme document. On insert, an ERPNext **Project** is created and the standard **Service Activities** are loaded. Use **Lifecycle Stage** to track where the project is in the pipeline.

### MICE Order and MICE Job

Phase orders scope work to one lifecycle stage (charges, milestones, documents). Phase jobs are execution documents with profitability tooling, similar to Project Job.

### Docket

Per-exhibitor working document under a **MICE Project** (scope, charges, milestones, documents, deliveries). Linked from the programme **Dockets** tab.

### Sales Quote

Set **Main Service** to **MICE** on a Sales Quote, enter the MICE Project name and open/close dates, and add charge lines with Service Type **MICE** (each line requires a **Site**). Use **Create MICE Project** on a submitted quote or **Get Charges from Quotation** on a draft MICE Project. Saving the quote back-fills customer and show fields on the project when empty.

## Typical workflow

1. Create **MICE Project** (or from Sales Quote with Main Service = MICE).
2. Complete scoping and set status to **Approved** — four **MICE Orders** are auto-created.
3. Use the **Jobs** tab (**Internal Job Detail**) to link Air/Sea/Transport/Warehouse legs or **MICE** resource rows.
4. Track the standard service activities on the **Lifecycle** tab; advance **Lifecycle Stage** when activities are complete (strict mode in MICE Settings).
5. Bill via the **Billings** tab and operational charge lines on the **Charges** tab.

## Settings

**MICE Settings** — default Project Type, milestone/document templates, strict lifecycle mode, auto-create phase orders.
