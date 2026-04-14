# Transport Template

**Transport Template** is a master that defines predefined transport configurations. It can store default legs, package types, vehicle types, and charges for quick order creation.

Use a Transport Template when creating Transport Orders or Transport Jobs to auto-fill common configurations.

To access Transport Template, go to:

**Home > Transport > Transport Template**

## 1. How to Create a Transport Template

1. Go to the Transport Template list, click **New**.
2. Enter **Template Name** (e.g., "Standard LTL", "Express Delivery").
3. Add **Legs** with default pickup/delivery logic if applicable.
4. Select **Default Vehicle Type** and **Default Load Type**.
5. Add **Charges** (default charge types and rates).
6. **Save** the document.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Template** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `section_break_xvtl` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `legs` | Table | **Purpose:** Stores repeating **Transport Template Leg** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Transport Template Leg (field `legs` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Facility Type From (`facility_type_from`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| `column_break_bjvj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Facility Type To (`facility_type_to`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Transport Order](welcome/transport-order)
- [Transport Job](welcome/transport-job)
- [Transport Settings](welcome/transport-settings)
