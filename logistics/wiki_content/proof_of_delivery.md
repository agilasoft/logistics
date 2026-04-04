# Proof of Delivery

**Proof of Delivery (POD)** is evidence that cargo was delivered. Captured at Transport Leg or via Run Sheet Scan (signature, photo, timestamp).

Access: **Home > Transport > Transport Leg** or [Run Sheet Scan](welcome/run-sheet-scan).


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Proof of Delivery** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_h5ry` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Proof of Delivery** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Proof of Delivery**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: POD.########. |

<!-- wiki-field-reference:end -->

## Related

- [Transport Leg](welcome/transport-leg)
- [Run Sheet](welcome/run-sheet)
- [Glossary](welcome/glossary)
