# CargoNext v2 — Bessel: List Notes

**Codename:** Bessel  
**Product:** CargoNext (`logistics` on Frappe / ERPNext)  
**Source of these notes:** the Python and desk scripts in this repository. GoConnect is a separate app this code calls. CargoNext AI has no module, client, or settings in this tree.

**Navigation:** Home > Introduction > CargoNext v2 — Bessel List Notes

v1 behaviour is in [CargoNext v1 — Release Notes](welcome/release-notes-v1). Later deltas on the same line are in [Recent Platform Updates](welcome/recent-platform-updates).

---

## 1. What this repository wires to GoConnect

GoConnect is optional for sea maps and Master Bill voyage actions. Those paths check `frappe.get_installed_apps()` and return a message when `goconnect` is absent.

Flight schedule imports and the land telematics imports are direct (`from goconnect...`). Those modules do not load unless the app is installed.

`logistics.utils.goconnect` is the safe caller. `call` looks up a dotted path with `frappe.get_attr`, returns `None` when the app or the path is missing, and refuses any path that does not start with `goconnect.`. `safe_call` logs and returns a default instead of raising. Master Bill uses `call`. The sea map and the flight code do not.

The CargoNext dock order in `desk_main_sidebar_visibility_fix.js` applies only when `app_name` is `logistics`. Any other app, GoConnect included, keeps the dock and icons Frappe resolved.

Sea Freight Settings no longer stores vessel provider, API user, API key, or API secret. Patch `v1_8_drop_sea_freight_settings_vessel_tracking_fields` drops those columns and deletes the matching `__Auth` password rows. The settings form shows a notice that points at **GoConnect Settings ▸ Vessel**.

---

## 2. Sea — vessel position and voyage

### 2.1 Live dot on the Sea Shipment dashboard

`get_vessel_tracking_map_options_for_sea_shipment` decides whether the dashboard map may ask for a position.

- A cancelled shipment (`docstatus` 2) stays off, with no hint.
- An unsaved shipment gets the hint to save first.
- Tracking is on only when `goconnect` is installed and `goconnect.sea.aggregator.get_aggregator().providers()` returns at least one provider. Otherwise the hint says to enable a provider in **GoConnect Settings ▸ Vessel**.
- Identity is resolved by `goconnect.sea.resolve.get_or_resolve_ids_for_sea_shipment`. That resolver is also described as walking Master Bill → Vessel Schedule when the routing leg has no Vessel master.
- If that call misses, this app walks the in-memory routing legs: the Main sea leg’s `vessel_master`, then the first sea leg that has one. The Vessel master must be active and must have MMSI or IMO. Missing either produces a hint. If the master has an id and GoConnect’s resolver still missed, the map is enabled anyway.

When enabled, the dashboard script calls `goconnect.api.sea.get_vessel_position_for_map` directly (not the logistics wrapper). First fetch is after 1.5 seconds, then every 60 seconds while the badge is on the page and the tab is visible. A successful payload with `lat` and `lon` drops a marker on Leaflet, Google, or MapLibre. The badge reads `sog` (knots), `cog`, `heading`, and a link to `vessel_schedule` when the payload includes one. Stale, cache, and error states come from `source`, `stale`, and the message text.

`logistics.sea_freight.vessel_tracking.api.get_vessel_position_for_map` is a whitelist that forwards the same GoConnect function for old callers. It returns the install message when the app is missing.

The Marinesia, VesselAPI, and VesselFinder modules under `logistics/sea_freight/vessel_tracking/providers/` are not imported by the map or the Master Bill. VesselFinder’s `fetch_position` returns `None`.

### 2.2 Master Bill voyage actions

On a saved Master Bill the **Action** menu adds **Refresh Voyage Status**. It calls `refresh_voyage_status`.

- No GoConnect: `success` false, `app_installed` false, and the current voyage fields. The form title is “GoConnect required”.
- No linked Vessel Schedule: the message tells the user to auto-link first. This function does not read the **Auto-Update from Vessel Schedule** checkbox.
- Otherwise it calls `goconnect.api.sea.sync_voyage_data` with the linked schedule. A `PermissionError` comes back as `licensed` false. The form title is “Subscription required”, and the fallback text says the license does not cover the vessel voyage tracker.
- On success the bill is reloaded. The response returns `voyage_status`, `actual_departure`, `actual_arrival`, `last_position_update`, `current_latitude`, `current_longitude`, `current_speed_knots`, and `provider` from the GoConnect result.

**Auto-link Vessel Schedule** shows only when `vessel_schedule` is empty. `fetch_and_link_vessel_schedule` requires a voyage number. It looks up DocType **Vessel Schedule** by `voyage_no` and, when set, `vessel_imo`. If none exists it inserts one (vessel link by vessel name, shipping line, origin and destination ports, scheduled departure and arrival, voyage status or “Scheduled”). It then writes that name onto the bill. The insert runs only after the install check. This repository does not define the Vessel Schedule DocType.

Voyage status on the bill is a read-only select: Scheduled, At Origin, Departed, In Transit, Arrived, At Destination, Delayed, Cancelled.

The checkbox **Auto-Update from Vessel Schedule** defaults on. Its description says GoConnect keeps status, ETA, ATD, ATA, and position in step with the schedule. No Python in this app reads that flag.

---

## 3. Air — schedules and live flights

Schedule connectors under `logistics/air_freight/flight_schedules/` are re-exports of `goconnect.flight`: aggregator, OpenSky, AviationStack, Aviation Edge, ADS-B aggregator, cache, master-data sync, and tasks. The Air Freight workspace links **GoConnect Settings (Flight)** to DocType **GoConnect Settings**.

### 3.1 Settings this app reads

`flight_schedule_api.get_flight_schedule_settings` and `get_available_providers` load **GoConnect Settings** and read:

- `flight_default_provider`
- `flight_enable_auto_fallback`
- `flight_cache_duration_hours`
- `flight_sync_frequency`
- `flight_enable_realtime_tracking`
- `flight_max_api_calls_per_hour`
- `flight_data_retention_days`
- `flight_test_mode`
- `flight_debug_logging`
- `opensky_enabled`, `aviationstack_enabled`, `aviation_edge_enabled`, `flightaware_enabled`

`get_available_providers` labels the four providers:

- OpenSky Network — real-time tracking, ADS-B, geographic queries
- AviationStack — schedules, airport schedules, route search, airlines, airports
- Aviation Edge — schedules, airport timetables, routes
- FlightAware — predictive ETAs, historical data, alerts

Whitelisted schedule calls (`search_flights`, `get_flight_status`, `get_airport_schedule`, `get_real_time_flight`, `sync_flight_data`, airport and airline master sync) go through the GoConnect aggregator re-export.

### 3.2 One Air Shipment on the dashboard map

The air dashboard turns the overlay on when the shipment has a Master Air Waybill and that bill has `flight_schedule`. The script calls `logistics.air_freight.api.live_flight_tracking.get_aircraft_position_for_map`.

That method checks read permission, then requires the Master AWB → Flight Schedule link. It reads **GoConnect Settings**. If `flight_enable_realtime_tracking` is off, the status is `disabled`. If it is on, the response is the position already stored on the Flight Schedule. A refresh is queued when the stored fix is missing or older than 45 seconds, and only once per Flight Schedule per 60 seconds (`logistics:af_live_enqueue:`). The queued job is `refresh_air_shipment_flight_position`.

The background job bails out unless both `flight_enable_realtime_tracking` and `opensky_enabled` are on. It builds ADS-B callsigns from the IATA flight number and the ICAO airline code, then asks providers in order:

1. OpenSky, only when `opensky_enabled` is set, with a bounding box around the shipment and a 20 second timeout.
2. `AdsbAggregatorConnector` (adsb.lol, then adsb.fi), 10 second timeout.

A match is written onto the Flight Schedule: latitude, longitude, altitude, speed, heading, vertical speed, on-ground, last position time, `sync_status` Synced, and `data_source`. The badge states the script understands are LIVE, ON GROUND, STALE, FETCHING, DISABLED, NO ADS-B, NO CALLSIGN, UNREACHABLE, NO FIX, and ERROR. Metrics shown are altitude (metres), speed (km/h), and heading.

### 3.3 Operations dashboard list

`get_live_operational_flights` loads Flight Schedules that a Master Air Waybill references from an Air Shipment in the session company. Draft shipments are included. Cancelled shipments are excluded. Statuses considered trackable on a schedule are Scheduled, Active, EnRoute, Delayed, Diverted, and Landed.

This list path calls OpenSky only, and only when both `flight_enable_realtime_tracking` and `opensky_enabled` are on. It does not fall through to the ADS-B aggregators. One `get_states_for_callsigns` covers every candidate on screen. A live fix wins. Otherwise the last stored fix is shown, and a stored fix with no live state is stale after 60 minutes. The map colours a live airborne fix blue, a live on-ground fix grey, a stale fix amber, and a fix with no position grey.

### 3.4 Scheduled jobs registered on the logistics app

`logistics/hooks.py` registers the flight re-exports:

- Every 10 minutes: `flight_schedules.tasks.sync_active_flights`
- Hourly: `flight_schedules.tasks.update_air_freight_jobs_with_flight_status`
- Daily: `flight_schedules.tasks.cleanup_old_schedules` and `cleanup_old_sync_logs`

Those names import `goconnect.flight.tasks` when the job module loads. The comment on the shim says the same jobs are also registered from `goconnect/hooks.py`.

---

## 4. Land — vehicle telematics

Provider execution is re-exported from `goconnect.land`: `make_provider`, `_provider_conf`, `resolve_vehicle_provider`, and `jobs.tick`. CargoNext still owns the masters and the vehicle form.

**Telematics Provider** `provider_type` is one of REMORA, TRACCAR, WIALON, GEOTAB, SAMSARA, CUSTOM. The form stores base URL, API key, username, password, timeout, and enabled. Remora adds a SOAP endpoint override, namespace, and SOAP version.

**Transport Vehicle** stores `telematics_provider`, `telematics_external_id`, and `telematics_device_name`. **Transport Settings** holds `default_telematics_provider`. On validate, an empty vehicle provider is filled from that default.

Form actions, when an external id is set:

- **Get Latest Position** calls `get_latest_position`. That loads provider config, `make_provider`, and `fetch_latest_positions()`, then matches `external_id` or `device_id`. It writes `last_telematics_ts`, `last_telematics_lat`, `last_telematics_lon`, `last_speed_kph`, `last_ignition_on`, `last_odometer_km`, `last_fuel_level`, and `last_provider`. Fuel prefers `fetch_latest_can_data()` matched on `device_id`, then fuel on the position.
- **Get CAN Data** calls `get_can_data` and returns timestamp, fuel, RPM, engine hours, coolant temperature, and ambient temperature. Fuel is saved on `last_fuel_level`.
- **View on Map** opens the last lat/lon.
- **View All Devices** calls `logistics.transport.api_telematics_debug.get_all_device_ids`.
- **Fetch Device ID** (`fetch_device_id`) matches `telematics_device_name` to a provider device and writes `telematics_external_id`. Remora device rows are read with `_get_field`.

The transport portal, transport job detail, and driver page read `last_telematics_lat` / `last_telematics_lon` (and the portal also reads `last_telematics_ts`) for the customer map. They do not call the provider themselves.

`logistics/transport/hooks.py` lists `logistics.transport.telematics.jobs.tick` every 2 minutes. `logistics/hooks.py` does not import that file and does not register the tick. The tick symbol is `goconnect.land.jobs.tick`.

---

## 5. CargoNext AI

A search of this repository’s Python, JavaScript, and DocType JSON finds no `cargonext_ai` app, no assistant client, no model call, and no AI settings DocType. `modules.txt` does not list it. Nothing in `hooks.py` loads it.

There is no CargoNext AI feature list to take from this code.

---

## 6. How to read these notes

- Sections 2 to 4 are the GoConnect behaviours implemented or called from this app.
- Section 5 is the result of looking for CargoNext AI in this app.
- Sea, air, transport, customs, warehousing, pricing, and job costing from v1 are unchanged by this page. See [CargoNext v1 — Release Notes](welcome/release-notes-v1).

**Support:** info@agilasoft.com · [www.agilasoft.com](https://www.agilasoft.com)

---

<!-- wiki-field-reference:start -->

## Complete field reference

_List notes only. Voyage fields on the bill are on [Master Bill](welcome/master-bill). Vessel tracking setup is described on [Sea Freight Settings](welcome/sea-freight-settings). Vehicle telematics fields are on [Transport Settings](welcome/transport-settings)._

<!-- wiki-field-reference:end -->
