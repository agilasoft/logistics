# Exhibits Module

**Exhibits** manages trade-show and exhibit programmes across four lifecycle stages: **Pre-Show**, **Logistics**, **On-Site**, and **Post-Show**. Each programme links to an ERPNext **Project**, supports multimodal operational jobs, charges, milestones, and documents—aligned with the Special Projects pattern.

Go to **Home > Events** to open the workspace.

## Key concepts

### Show

The main programme document. On insert, an ERPNext **Project** is created and twelve standard **Service Activities** are loaded. Use **Lifecycle Stage** to track where the show is in the pipeline.

### Event Order and Event Job

Phase orders scope work to one lifecycle stage (charges, milestones, documents). Phase jobs are execution documents with profitability tooling, similar to Project Job.

### Event Plan

Scoped commercial and delivery plan under an **Show** (scope, charges, milestones, documents). Linked from the programme **Connections** tab.

### Sales Quote

Set **Main Service** to **Exhibits** on a Sales Quote, enter exhibit name and open/close dates, and add charge lines with Service Type **Exhibits** (each line requires a **Site**). Use **Create Exhibit** on a submitted quote or **Get Charges from Quotation** on a draft Exhibit programme. Saving the quote back-fills customer and show fields on the programme when empty.

## Typical workflow

1. Create **Show** (or from Sales Quote with Main Service = Events).
2. Complete scoping and set status to **Approved** — four **Event Orders** are auto-created.
3. Use the **Jobs** tab (**Internal Job Detail**) to link Air/Sea/Transport/Warehouse legs or **Events** resource rows.
4. Track the twelve service activities on the **Lifecycle** tab; advance **Lifecycle Stage** when activities are complete (strict mode in Event Settings).
5. Bill via the **Billings** tab and operational charge lines on the **Charges** tab.

## Settings

**Event Settings** — default Project Type, milestone/document templates, strict lifecycle mode, auto-create phase orders.
