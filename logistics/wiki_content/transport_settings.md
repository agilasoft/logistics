# Transport Settings

**Transport Settings** is a single-document configuration that defines default values and behavior for the Transport module. It controls routing, telematics, constraints, loading/unloading times, carbon footprint, and automation.

To access Transport Settings, go to:

**Home > Transport > Transport Settings**

## 1. Prerequisites

Before configuring Transport Settings, ensure the following are set up:

- [Load Type](welcome/load-type) – For capacity and planning
- [Vehicle Type](welcome/vehicle-type) – For transport planning
- [Transport Capacity Settings](welcome/transport-capacity-settings) – For capacity management

## 2. How to Configure

1. Go to **Transport Settings** (single document; no list).
2. Configure each tab as needed.
3. **Save** the document.

## 3. Features

### 3.1 Transport Plan

- **Forward Days in Transport Plan** – Days ahead to plan
- **Backward Days in Transport Plan** – Days back to include in plan

### 3.2 Automation

- **Enable Auto Billing** – Automatically create invoices for transport jobs
- **Enable Auto Vehicle Assignment** – Automatically assign vehicles to legs

### 3.3 Routing

- **Routing Provider** – OSRM, Mapbox, Google for route calculation
- **OSRM Base URL** – OSRM server URL
- **Routing Mapbox API Key** – Mapbox API key
- **Routing Google API Key** – Google Maps API key
- **Routing Default Avg Speed (km/h)** – Default speed for time estimation
- **Routing Auto Compute** – Automatically compute routes
- **Routing Show Map** – Show map on transport forms
- **Map Renderer** – Map display engine
- **Use Routing Service for Distance** – Use routing API for distance
- **Cache Route Distances** – Cache distances for performance
- **Distance Cache TTL Hours** – Cache validity period

### 3.4 Telematics

- **Default Telematics Provider** – Telematics integration
- **Telematics Poll Interval (min)** – How often to poll vehicle data

### 3.5 Constraint Features

- **Enable Constraint System** – Enable transport planning constraints
- **Constraint Checking Mode** – Strict or warning mode
- **Enable Time Window Constraints** – Respect delivery time windows
- **Enable Address Day Availability** – Restrict by day of week
- **Enable Plate Coding Constraints** – Restrict by vehicle plate
- **Enable Truck Ban Constraints** – Respect truck bans
- **Enable Adhoc Factors** – Allow ad-hoc delay/blocking factors
- **Require Vehicle Avg Speed** – Require speed for planning
- **Allow Vehicle Assignment with Warnings** – Allow assignment despite warnings
- **Block Incompatible Vehicle Types in Consolidation** – Prevent incompatible consolidations

### 3.6 Loading/Unloading

- **Default Base Loading Time (minutes)** – Base time for loading
- **Default Loading Time Calculation Method** – By volume, weight, or fixed
- **Default Loading Time Per Volume (m³)** – Minutes per CBM
- **Default Loading Time Per Weight (kg)** – Minutes per kg
- **Default Base Unloading Time (minutes)** – Base time for unloading
- **Default Unloading Time Calculation Method** – Same options as loading

### 3.7 Adhoc Factors

- **Adhoc Factor Delay Threshold (minutes)** – When to apply delay factors
- **Adhoc Factor Blocking Impact Types** – Which impact types block planning

### 3.8 Default UOM

- **Default Weight UOM** – kg, lb
- **Default Volume UOM** – CBM, CFT
- **Default Chargeable UOM** – For charges
- **Volume to Weight Divisor** – For chargeable weight

### 3.9 Carbon

- **Carbon Autocompute** – Automatically calculate carbon footprint
- **Carbon Default Factor (g/km)** – Default emission factor per km
- **Carbon Default Factor (g/ton-km)** – Default emission factor per ton-km
- **Carbon Provider** – External carbon calculation provider
- **Carbon Provider API Key** – API key for provider
- **Carbon Provider URL** – Provider endpoint


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Forward Days in Transport Plan (`forward_days_in_transport_plan`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Backward Days in Transport Plan (`backward_days_in_transport_plan`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Automation (`automation_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Workflow Automation (`automation_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Auto Billing (`enable_auto_billing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Auto Vehicle Assignment (`enable_auto_vehicle_assignment`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing (`routing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Routing Provider (`routing_provider`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Disabled, OSRM, Mapbox, Google. |
| OSRM Base URL (`osrm_base_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| Mapbox API Key (`routing_mapbox_api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Google API Key (`routing_google_api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Default Avg Speed (KPH) (`routing_default_avg_speed_kmh`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_rifi` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Routing Auto Compute (`routing_auto_compute`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing Show Map (`routing_show_map`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Map Renderer (`map_renderer`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: OpenStreetMap, Google Maps, Mapbox, MapLibre. |
| Maps Enable External Links (`maps_enable_external_links`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing Tiles URL (`routing_tiles_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| Routing Tiles Attr (`routing_tiles_attr`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Routing Timeout (sec) (`routing_timeout_sec`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Telematics (`telematics_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Default Telematics Provider (`default_telematics_provider`) | Link | **Purpose:** Creates a controlled reference to **Telematics Provider** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Telematics Provider**. Create the master first if it does not exist. |
| Telematics Poll Interval (min) (`telematics_poll_interval_min`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Constraint Features (`constraint_features_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Constraint Features (`section_constraint_features`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Constraint System (`enable_constraint_system`) | Check | **From definition:** Master switch to enable/disable all constraint checking in vehicle selection **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Constraint Checking Mode (`constraint_checking_mode`) | Select | **From definition:** Strict: Block vehicle assignment if constraints fail Warning: Allow assignment but show warnings Disabled: Skip constraint checking **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Strict, Warning, Disabled. |
| `column_break_constraints` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Time Window Constraints (`enable_time_window_constraints`) | Check | **From definition:** Check pick/drop time windows when assigning vehicles **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Address Day Availability (`enable_address_day_availability`) | Check | **From definition:** Check day-of-week restrictions for pick/drop operations **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Plate Number Coding Constraints (`enable_plate_coding_constraints`) | Check | **From definition:** Check license plate coding restrictions (odd/even days, last digit rules) **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Truck Ban Constraints (`enable_truck_ban_constraints`) | Check | **From definition:** Check area and time-based truck ban restrictions **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Ad-Hoc Transport Factors (`enable_adhoc_factors`) | Check | **From definition:** Consider ad-hoc factors (road closures, port congestion, etc.) in planning **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Routing and Travel Time (`section_routing_constraints`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Use Routing Service for Distance (`use_routing_service_for_distance`) | Check | **From definition:** Use routing provider API to calculate distances (if available) **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Require Vehicle Average Speed (`require_vehicle_avg_speed`) | Check | **From definition:** If checked, skip vehicles without avg_speed set (instead of using default) **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Cache Route Distances (`cache_route_distances`) | Check | **From definition:** Cache calculated distances for performance **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Distance Cache TTL (hours) (`distance_cache_ttl_hours`) | Int | **From definition:** Time to live for distance cache entries **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Loading and Unloading Time Defaults (`section_loading_unloading`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Base Loading Time (minutes) (`default_base_loading_time_minutes`) | Float | **From definition:** Default base loading time if not specified in Pick Mode or Address **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Default Loading Time Calculation Method (`default_loading_time_calculation_method`) | Select | **From definition:** Default method for calculating loading time **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Fixed Time, Volume-Based, Weight-Based, Volume and Weight Combined. |
| Default Loading Time per m³ (minutes) (`default_loading_time_per_volume_m3`) | Float | **From definition:** Default additional minutes per cubic meter of volume **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Default Loading Time per 100kg (minutes) (`default_loading_time_per_weight_kg`) | Float | **From definition:** Default additional minutes per 100kg of weight **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Default Base Unloading Time (minutes) (`default_base_unloading_time_minutes`) | Float | **From definition:** Default base unloading time if not specified in Drop Mode or Address **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Default Unloading Time Calculation Method (`default_unloading_time_calculation_method`) | Select | **From definition:** Default method for calculating unloading time **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Fixed Time, Volume-Based, Weight-Based, Volume and Weight Combined. |
| Default Unloading Time per m³ (minutes) (`default_unloading_time_per_volume_m3`) | Float | **From definition:** Default additional minutes per cubic meter of volume **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Default Unloading Time per 100kg (minutes) (`default_unloading_time_per_weight_kg`) | Float | **From definition:** Default additional minutes per 100kg of weight **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Ad-Hoc Factors Settings (`section_adhoc_factors`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Ad-Hoc Factor Delay Threshold (minutes) (`adhoc_factor_delay_threshold_minutes`) | Int | **From definition:** Maximum delay from ad-hoc factors before blocking route assignment **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Ad-Hoc Factor Impact Types That Block Routes (`adhoc_factor_blocking_impact_types`) | Table | **From definition:** Impact types that will block route assignment (others will only add delays) **Purpose:** Stores repeating **Transport Settings Adhoc Factor Impact** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Performance Settings (`section_performance`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Constraint Cache (`constraint_cache_enabled`) | Check | **From definition:** Cache active constraints for better performance **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Constraint Cache Refresh Interval (minutes) (`constraint_cache_refresh_interval_minutes`) | Int | **From definition:** How often to refresh the constraint cache **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Max Constraint Check Timeout (seconds) (`max_constraint_check_timeout_seconds`) | Int | **From definition:** Maximum time allowed for constraint checking before timeout **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Validation Settings (`section_validation`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Warn on Missing Vehicle Average Speed (`warn_on_missing_vehicle_avg_speed`) | Check | **From definition:** Show warning when vehicle doesn't have avg_speed set **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Warn on Missing Cargo Volume (`warn_on_missing_cargo_volume`) | Check | **From definition:** Show warning when cargo volume cannot be calculated for loading/unloading time **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Allow Vehicle Assignment with Warnings (`allow_vehicle_assignment_with_warnings`) | Check | **From definition:** Allow vehicle assignment even if constraint warnings exist (when mode is Warning) **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Block Incompatible Vehicle Types in Consolidation (`block_incompatible_vehicle_types_in_consolidation`) | Check | **From definition:** When enabled, prevents saving consolidation when jobs have different vehicle types **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default UOM (Weight, Volume, Chargeable) (`default_uom_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Weight UOM (`default_weight_uom`) | Link | **From definition:** Default UOM for weight in Sales Quote Transport tab and transport-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Volume UOM (`default_volume_uom`) | Link | **From definition:** Default UOM for volume in Sales Quote Transport tab and transport-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Chargeable UOM (`default_chargeable_uom`) | Link | **From definition:** Default UOM for chargeable weight in Sales Quote Transport tab and transport-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Volume to Weight Divisor (`volume_to_weight_divisor`) | Float | **From definition:** Divisor for calculating volume weight. Formula: volume_weight = volume (m³) × 1,000,000 / divisor. Default: 3000 (common road transport standard = 333 kg/m³) **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Carbon (`carbon_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Carbon Autocompute (`carbon_autocompute`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Carbon Default Factor (g/km) (`carbon_default_factor_g_per_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Carbon Default Factor (g/Tkm) (`carbon_default_factor_g_per_ton_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_ezfi` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Carbon Provider (`carbon_provider`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: FACTOR_TABLE, CLIMATIQ, CARBON_INTERFACE, CUSTOM_WEBHOOK. |
| Carbon Provider API Key (`carbon_provider_api_key`) | Password | **Purpose:** Field type **Password** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Carbon Provider URL (`carbon_provider_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |
| `section_break_sdbl` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Emission Factors (`emission_factors`) | Table | **Purpose:** Stores repeating **Transport Emission Factor** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Transport Settings Adhoc Factor Impact (field `adhoc_factor_blocking_impact_types` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Impact Type (`impact_type`) | Link | **Purpose:** Creates a controlled reference to **Ad-Hoc Factor Impact Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Ad-Hoc Factor Impact Type**. Create the master first if it does not exist. |

#### Child table: Transport Emission Factor (field `emission_factors` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Scope (`scope`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: PER_KM, PER_TON_KM. |
| Fuel Type (`fuel_type`) | Select | **Purpose:** Single choice from a configured list. **What to enter:** Select one option from the dropdown. |
| Factor (g/km) (`factor_g_per_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Factor (g/Tkm) (`factor_g_per_ton_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_cvno` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Source (`source`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Source URL (`source_url`) | Data | **Purpose:** Web address for tracking, authority, or carrier portals. **What to enter:** Full URL including https:// where applicable. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Transport Order](welcome/transport-order)
- [Transport Job](welcome/transport-job)
- [Transport Plan](welcome/transport-plan)
- [Run Sheet](welcome/run-sheet)
- [Transport Capacity Settings](welcome/transport-capacity-settings)
