# Transport Mode

**Transport Mode** is a master that defines how goods move (for example Air, Sea, Road, Rail). It is used on Sales Quotes, bookings, shipments, routing legs, customs declarations, and other logistics documents.

Each transport mode record indicates which services it applies to (**Air**, **Sea**, **Transport**, **Customs**, **Warehousing**) and can supply a default transport document type for customs.

To access Transport Mode, go to:

**Home > Logistics > Transport Mode**

## 1. How to Create a Transport Mode

1. Go to the Transport Mode list, click **New**.
2. Enter **Mode Code** (unique identifier, for example `Air`, `FCL`, `Road`).
3. Enter **Mode Name** and **Primary Document** (the main operational document for this mode).
4. Optionally set **Default Transport Document Type** for customs declarations.
5. Under **Used in Module**, check **Air**, **Sea**, **Transport**, **Customs**, and/or **Warehousing** as applicable.
6. Ensure **Is Active** is checked.
7. **Save** the document.

Module flags control which modes appear when a user selects a service type on forms such as Sales Quote and Opportunity Service Scopes. See [Load Type and Transport Mode — Service Type Validation](welcome/service-type-load-transport-validation) for setup and troubleshooting.

## 2. Related Topics

- [Load Type and Transport Mode — Service Type Validation](welcome/service-type-load-transport-validation)
- [Load Type](welcome/load-type)
- [Sales Quote](welcome/sales-quote)
- [Transport Leg](welcome/transport-leg)
- [Declaration Order](welcome/declaration-order)
