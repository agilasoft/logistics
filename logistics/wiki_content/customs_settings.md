# Customs Settings

**Customs Settings** is a single-document configuration that defines default values and behavior for the Customs module. It controls declaration defaults, compliance, document requirements, and integration options.

To access Customs Settings, go to:

**Home > Customs > Customs Settings**

## 1. Prerequisites

Before configuring Customs Settings, ensure the following are set up:

- Company, Branch (from ERPNext)
- [Customs Authority](welcome/customs-authority) – Customs authorities
- [Commodity](welcome/commodity) – HS code masters
- [Document List Template](welcome/document-list-template) – For document requirements

## 2. How to Configure

1. Go to **Customs Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new declarations
- **Default Branch** – Branch for customs operations
- **Default Customs Authority** – Default authority for declarations
- **Default Currency** – Currency for duty/tax

### 3.2 Declaration Settings

- **Default Declaration Type** – Import, Export, Transit
- **Require HS Code** – Require HS code for commodities
- **Require Commodity Description** – Require detailed description
- **Auto Calculate Duty** – Automatically calculate duty from rates

### 3.3 Document Settings

- **Default Document List Template** – Template for declaration documents
- **Require Commercial Invoice** – Mandatory for submission
- **Require Packing List** – Mandatory for submission
- **Require Bill of Lading** – Mandatory for import

### 3.4 Compliance Settings

- **Enable Compliance Alerts** – Alert for compliance issues
- **Compliance Check Interval** – How often to check
- **Enable Manifest Integration** – Integrate with manifest systems

### 3.5 Integration Settings

- **Enable Customs Clearance Tracking** – Track clearance status
- **Enable EDI Submission** – Submit declarations via EDI
- **Customs Portal URL** – Portal for manual submission

## 4. Related Topics

- [Declaration Order](welcome/declaration-order)
- [Declaration](welcome/declaration)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Document Management](welcome/document-management)
