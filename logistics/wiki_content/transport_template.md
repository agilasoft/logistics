# Transport Template

**Transport Template** is a master that defines predefined transport lane patterns, allowed load types, default load/vehicle types, and leg facility types for quick order and quote setup.

Use a Transport Template on **Sales Quote** (Transport main service), **Transport Order**, and **Transport Job** to auto-fill **Load Type** and **Vehicle Type** and to block incompatible combinations (for example FCL on a CFS→warehouse lane).

To access Transport Template, go to:

**Home > Transport > Transport Template**

## 1. How to Create a Transport Template

1. Go to the Transport Template list, click **New**.
2. Enter **Code** and **Description** (e.g. `CFS-WHS`, "CFS to warehouse drayage").
3. Add **Legs** — one row per lane segment with **Facility Type From** and **Facility Type To**.
4. Review **Allowed Load Types** — use the multiselect to pick permitted load types (suggested from legs when you add or change legs):
   - Land lanes (CFS, warehouse, shipper, consignee) → typically **FTL** / **LTL**
   - Container lanes (Terminal, Container Yard, Container Depot) → typically **FCL**
5. Set **Default Load Type** from the allowed list.
6. Optionally set **Default Vehicle Type** (must support the default load type).
7. **Save** — the system blocks save if legs and allowed load types conflict.

When a user selects this template on a quote or order, **Load Type** and **Vehicle Type** auto-fill if blank; dropdowns show only allowed values. **Location From/To** are still entered manually.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Template** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `section_break_defaults` | Section Break | **Purpose:** Visual grouping for default load/vehicle constraints. **What to enter:** No data — layout only. |
| Default Load Type (`default_load_type`) | Link | **Purpose:** Load type applied when this template is selected on a quote or order (if the field is blank). **What to enter:** Must be one of the **Allowed Load Types**. |
| Default Vehicle Type (`default_vehicle_type`) | Link | **Purpose:** Optional truck/equipment default when the template is selected. **What to enter:** Must allow the default load type on the **Vehicle Type** master. |
| Allowed Load Types (`allowed_load_types`) | Table MultiSelect | **Purpose:** Load types permitted for this template. **What to enter:** Select one or more **Load Type** values (e.g. FTL, LTL, or FCL). |
| `section_break_xvtl` | Section Break | **Purpose:** Visual grouping for leg rows. **What to enter:** No data — layout only. |
| `legs` | Table | **Purpose:** Stores repeating **Transport Template Leg** lines. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Transport Template Allowed Load Type (field `allowed_load_types` on parent)

Used as the options DocType for **Table MultiSelect**; rows are managed via the multiselect control on the parent form.

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Load Type (`load_type`) | Link | **Purpose:** One permitted load type for this template. **What to enter:** Active **Load Type** with **Transport** module enabled. |

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
- [Load Type and Transport Mode validation](welcome/service-type-load-transport-validation)
