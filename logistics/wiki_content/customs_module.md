# Customs Module

**Customs** covers import/export declarations, clearance, permits, and exemptions. In CargoNext, the Customs module manages: Sales Quote → Declaration Order → Declaration → Submission → Clearance → Release.

Industry terms: **HS Code** (Harmonized System), **Duty**, **Customs Broker**, **Manifest**, **AMS** (Automated Manifest System), **ISF** (Importer Security Filing).

To access the Customs workspace, go to:

**Home > Customs**

## 1. Typical Workflow

1. **Quote** – Create [Sales Quote](welcome/sales-quote) with customs legs
2. **Order** – Create [Declaration Order](welcome/declaration-order) from quote or manually
3. **Declaration** – Create [Declaration](welcome/declaration) from order
4. **Commodities** – Add [Commodity](welcome/commodity) lines with HS codes
5. **Documents** – Attach Commercial Invoice, Packing List, Bill of Lading, etc.
6. **Submit** – Submit to [Customs Authority](welcome/customs-authority)
7. **Permits** – Use [Permit Application](welcome/permit-application) if required
8. **Exemptions** – Use [Exemption Certificate](welcome/exemption-certificate) if applicable
9. **Billing** – Create [Sales Invoice](welcome/sales-invoice)

## 2. Key Concepts

### 2.1 HS Code

The Harmonized System code classifies commodities for duty calculation. Maintain in [Commodity](welcome/commodity) master.

### 2.2 Declaration Types

- **Import** – Inbound cargo
- **Export** – Outbound cargo
- **Transit** – Cargo in transit

### 2.3 Global Customs

CargoNext supports country-specific manifests: US AMS, US ISF, CA eManifest Forwarder, JP AFR. Configure in [Customs Settings](welcome/customs-settings) and [Manifest Settings](welcome/manifest-settings).

## 3. Workspace Structure

### 3.1 Quick Access

- Sales Quote, Declaration Order, Declaration, Permit Application, Exemption Certificate, Sales Invoice

### 3.2 Master Data

- [Commodity](welcome/commodity), [Customs Authority](welcome/customs-authority)
- Permit Type, Exemption Type, Exemption Certificate, Other Commodity Code

### 3.3 Reports

- **Dashboards:** Customs Dashboard, Global Customs Dashboard
- **Status:** Declaration Status Report, Manifest Status Report
- **Compliance:** Customs Compliance Report, Filing Compliance Report
- **Value:** Declaration Value Report

## 4. Related Topics

- [Getting Started](welcome/getting-started)
- [Customs Settings](welcome/customs-settings)
- [Declaration Order](welcome/declaration-order)
- [Declaration](welcome/declaration)
- [Glossary](welcome/glossary)
