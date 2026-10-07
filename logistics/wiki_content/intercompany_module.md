# Intercompany Module

**Intercompany** manages transactions between companies in the same group. It supports intercompany invoicing and reconciliation.

To access: **Home > Intercompany**

## 1. Key Concepts

### 1.1 Intercompany Settings

**Intercompany Settings** – Configuration for intercompany transactions: default companies, accounts, and rules.

### 1.2 Intercompany Invoice Log

**Intercompany Invoice Log** – Log of intercompany invoices created and their status. Tracks invoices between group companies for reconciliation.

### 1.3 Operating company cost vs intercompany invoice

The intercompany **Sales Invoice** / **Purchase Invoice** pair is the charge between the operating company and the Main Job’s company. It does not post the operating company’s own internal tariff.

On the operating company’s job, a charge with **Internal** and **Use Tariff in Cost** is posted with **Post → Standard Costs**: one Journal Entry, debit the item **Standard Cost Account**, credit **Applied Standard Cost Account**. That line is left off the supplier Purchase Invoice. Supplier costs on the same job still use a Purchase Invoice.

Full rules, documents, and the same-company case: [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing).


<!-- wiki-field-reference:start -->

## Complete field reference

_See **Complete field reference** on the documents you invoice or receive:_

- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Declaration](welcome/declaration), [Warehouse Job](welcome/warehouse-job)

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing) – how logistics jobs bill each other (JV vs SI/PI)
- [Recent Platform Updates](welcome/recent-platform-updates)
- [Logistics Settings](welcome/logistics-settings)
- [Getting Started](welcome/getting-started)
