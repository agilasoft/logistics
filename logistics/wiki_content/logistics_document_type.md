# Logistics Document Type

**Logistics Document Type** is a master that defines the standard document types used across CargoNext for document tracking. Examples include Commercial Invoice (CI), Packing List (PL), Bill of Lading (BL), Air Waybill (AWB), Certificate of Origin, and Proof of Delivery.

Each document type has a code, name, category (Trade, Transport, Customs, Insurance, DG, Other), typical format (PDF, Image, Excel, Any), and whether it has an expiry date.

To access Logistics Document Type, go to:

**Home > Logistics > Logistics Document Type**

## 1. How to Create a Logistics Document Type

1. Go to the Logistics Document Type list, click **New**.
2. Enter **Document Code** (e.g., "CI", "PL", "BL").
3. Enter **Document Name** (e.g., "Commercial Invoice").
4. Select **Category** (Trade, Transport, Customs, Insurance, Dangerous Goods, Other).
5. Select **Typical Format** (PDF, Image, Excel, Any).
6. Check **Has Expiry** if the document has a validity period.
7. **Save** the document.

## 2. Standard Document Types (Examples)

- Commercial Invoice (CI)
- Packing List (PL)
- Bill of Lading (BL)
- Air Waybill (AWB)
- Certificate of Origin (COO)
- Export License
- Import License / Permit
- Insurance Certificate
- Phytosanitary Certificate
- Fumigation Certificate
- Dangerous Goods Declaration (DGD)
- Delivery Order (DO)
- CMR / Cargo Manifest
- Proof of Delivery (POD)


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Logistics Document Type** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Document Code (`document_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Document Name (`document_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Category (`category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Trade, Transport, Customs, Insurance, Dangerous Goods, Other. |
| Typical Format (`typical_format`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: PDF, Image, Excel, Any. |
| Options (`section_break_options`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Has Expiry Date (`has_expiry`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Product Specific (`is_product_specific`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Document List Template](welcome/document-list-template)
- [Document Management](welcome/document-management)
