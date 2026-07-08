# Load Type and Transport Mode — Service Type Validation

**Load Type** and **Transport Mode** selections are validated against the active **service type** (for example **Main Service** on a Sales Quote, or **Service Type** on an Opportunity scope row). When the service is **Air**, only masters marked for **Air** appear in the dropdown; the same applies for **Sea**, **Transport**, **Customs**, and **Warehousing**.

This prevents incompatible combinations (for example a sea-only transport mode on an air quote) at data entry and on save.

**Transport Template** adds a second layer for **Transport** main-service quotes and transport orders: when a **Transport Template** is selected, **Load Type** and **Vehicle Type** must match that template's **Allowed Load Types**. See [Transport Template](welcome/transport-template).

## 1. Prerequisites

Before using filtered Load Type and Transport Mode fields, configure the master records:

- [Load Type](welcome/load-type)
- [Transport Mode](welcome/transport-mode)

Each master has **Used in Module** checkboxes: **Air**, **Sea**, **Transport**, **Customs**, and **Warehousing**. A record can have more than one checkbox enabled (for example a multimodal load type).

## 2. How to Set Up Load Type Masters

1. Go to **Home > Transport > Load Type** (or open the Load Type list from search).
2. Open an existing record or click **New**.
3. Enter **Load Type Name** and **Description**.
4. Under **Used in Module**, tick every service the load type applies to:
   - **Air** — air freight (for example ULD, loose)
   - **Sea** — sea freight (for example FCL, LCL)
   - **Transport** — land transport jobs
   - **Customs** — customs-related scopes
   - **Warehousing** — warehousing scopes
5. Ensure **Is Active** is checked.
6. **Save**.

**Examples**

| Load Type | Air | Sea | Transport | Notes |
|-----------|-----|-----|-----------|-------|
| ULD | ✓ | | | Air only |
| FCL | | ✓ | | Sea only |
| Palletized | ✓ | ✓ | ✓ | Multimodal |

If a valid option is missing on a form, open that Load Type and enable the checkbox for the current service.

## 3. How to Set Up Transport Mode Masters

1. Go to **Home > Logistics > Transport Mode**.
2. Open an existing record or click **New**.
3. Enter **Mode Code**, **Mode Name**, and **Primary Document**.
4. Under **Used in Module**, tick every service the mode applies to (same flags as Load Type).
5. Ensure **Is Active** is checked.
6. **Save**.

**Examples**

| Transport Mode | Air | Sea | Transport | Notes |
|----------------|-----|-----|-----------|-------|
| Air | ✓ | | | Air freight |
| Sea / FCL | | ✓ | | Sea freight |
| Road | | | ✓ | Land transport |

Standard install data creates common modes (Air, Sea, Road, Rail, and others). Review each record and set module flags to match how your company uses them.

## 4. Sales Quote (Regular and One-off)

On **Regular** and **One-off** quotes, **Main Service Parameters** includes **Load Type** and **Transport Mode**.

1. Create a **Sales Quote** with **Quotation Type** = **Regular** or **One-off**.
2. Set **Main Service** first (for example **Air**).
3. Open **Load Type** and **Transport Mode** — only active masters with the matching module flag are listed.
4. If you change **Main Service**, any Load Type or Transport Mode that no longer matches is cleared automatically.
5. On **Save**, incompatible combinations are rejected with a validation message.

**Charge lines:** Each charge row **Service Type** also filters **Load Type** on that row (same module flags).

See [Sales Quote](welcome/sales-quote) for full quote workflow.

## 5. Opportunity (Service Scopes)

On an **Opportunity**, each row in **Service Scopes** has its own **Service Type**, **Load Type**, and **Transport Mode**.

1. Add a scope row.
2. Set **Service Type** first (for example **Sea**).
3. **Load Type** and **Transport Mode** on that row show only masters applicable to that service.
4. Changing **Service Type** clears incompatible Load Type or Transport Mode values on that row.

## 6. Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Expected Load Type or Transport Mode not in the list | Open the master; enable the correct **Used in Module** checkbox; ensure **Is Active** is on. |
| Value cleared after changing service type | Previous selection was not valid for the new service — pick a matching master. |
| Save blocked with “not valid for Main Service” | Selected master does not have the module flag for the current service — change the selection or update the master. |
| Dropdown still shows all records | Hard-refresh the browser (**Ctrl+Shift+R**) so updated form scripts load. |

## 7. Related Topics

- [Load Type](welcome/load-type)
- [Transport Mode](welcome/transport-mode)
- [Sales Quote](welcome/sales-quote)
- [Transport Settings](welcome/transport-settings)
