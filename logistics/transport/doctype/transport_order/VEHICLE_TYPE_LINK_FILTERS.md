# Vehicle Type filtering on Transport Order

Vehicle Type is filtered by **load_type**, **hazardous**, and **reefer** entirely in the form script (`transport_order.js`) via **get_query**.

**Do not set Link Filters on the Vehicle Type field in Edit DocType.**  
If the field has `link_filters` in JSON, Frappe’s Link control replaces `get_query` with a function that only returns those filters. That overwrote the script’s get_query and prevented load_type (Allowed Load Types) from being applied. The Vehicle Type field has no `link_filters` in JSON; all filters come from get_query.

- **load_type** — Vehicle Types that have the selected Load Type in **Allowed Load Types** (via server method + cache).
- **hazardous** — `hazardous` equals the order’s hazardous checkbox.
- **reefer** — `reefer` equals the order’s reefer checkbox.
