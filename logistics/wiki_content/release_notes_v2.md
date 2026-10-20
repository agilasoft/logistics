# CargoNext v2 — Bessel: List Notes

**Codename:** Bessel  
**Product:** CargoNext (logistics app for Frappe / ERPNext), with companion apps **CargoNext AI** and **GoConnect**  
**Partners:** Agilasoft Cloud Technologies Inc. · BlueCore Solutions Corp.  
**Status:** [cargonext.io/v2-bessel](https://www.cargonext.io/v2-bessel) still marks this version as under development. These are working list notes for the version line, not a general-availability announcement.

**Navigation:** Home > Introduction > CargoNext v2 — Bessel List Notes

v1 scope stays in [CargoNext v1 — Release Notes](welcome/release-notes-v1). Behaviour already on the current line stays in [Recent Platform Updates](welcome/recent-platform-updates).

---

## 1. Version line

- Follows **CargoNext v1 — Astraea**.
- Public product page: [CargoNext v2 Bessel](https://www.cargonext.io/v2-bessel).
- Recorded scope lives on GitHub milestone **v2.0 Bessel Feature List** (issues [#820](https://github.com/agilasoft/logistics/issues/820)–[#824](https://github.com/agilasoft/logistics/issues/824)).
- Two companion apps sit beside the logistics app on a CargoNext site:
  - **GoConnect** (`goconnect`) — live sea, air, and land tracking.
  - **CargoNext AI** (`cargonext_ai`) — the desk assistant labelled CARGO AI.
- Platform baseline is the same as v1: Frappe v16+, ERPNext v16+, Python 3.14+.

---

## 2. Recorded Bessel scope

These bullets are the feature list recorded on the v2.0 milestone. They are the version’s scope notes. They are not a claim that every item already ships in this repository.

### 2.1 Project cargo

- Project cargo for oversized, heavy-lift, time-critical, and multi-leg movements: structured scope, milestones, and documentation.
- Special Projects stays the shared planning surface (scope, resources, milestone billing).
- Fairs and exhibits: booth and build schedules, move-in and move-out dates, carnets and exhibit documents, and repeatable event profiles.

Source: [#820](https://github.com/agilasoft/logistics/issues/820).

### 2.2 Risk and control

- Risk registers at module level, tied to jobs, legs, customs steps, warehousing, and project milestones.
- Approvals that keep duties separate, mandatory checkpoints before key transitions, and an audit trail on sensitive changes.
- Guided workflows, reusable templates, safe bulk actions, and defaults from customer or project profiles.
- Cutoff warnings, SLA timers with escalation, and dashboards that show penalty and delay exposure before the deadline.

Source: [#821](https://github.com/agilasoft/logistics/issues/821).

### 2.3 Tracking integrators

- One aggregator pattern for status events (booking confirmed, departed, arrived, customs hold, proof of delivery) mapped onto milestones.
- Near-real-time updates by webhook or partner polling, queued so the desk and notifications move without a manual refresh.
- The same connector approach across sea, air, transport, customs, warehousing, and project cargo.

Source: [#822](https://github.com/agilasoft/logistics/issues/822).

### 2.4 Notice to Explain and quality

- Operational alerts (deadlines, deviations, document gaps) can be promoted into a Notice to Explain with the job context attached.
- A non-compliance case can hang off that notice so the corrective action, owner, and closure stay on one trail.
- The audit story is: who was notified, what was explained, what was corrected, and which job or quality record it belongs to.

Source: [#823](https://github.com/agilasoft/logistics/issues/823).

### 2.5 Operations of the connectors

- Integration health per provider: success, latency, and errors, plus replay of failed events and an admin screen for connector setup.
- Secrets handling for API keys, role-based access to Notice to Explain and quality records, and retention that follows policy.

Source: [#824](https://github.com/agilasoft/logistics/issues/824).

---

## 3. GoConnect

GoConnect is the tracking app. CargoNext calls it at runtime and keeps working when a licensed tracker is absent: vessel maps show a hint, and Master Bill refresh returns the bill as it stands. Configure providers in **GoConnect Settings**. CargoNext does not store those API keys on Sea Freight Settings anymore.

The CargoNext dock order applies only inside the logistics app. GoConnect keeps the dock and icons Frappe resolved for it.

### 3.1 Sea — vessel and voyage

- **GoConnect Settings ▸ Vessel** holds providers, API keys, cache TTL, and fallback order. Sea Freight Settings only shows a pointer to that screen.
- **Vessel Schedule** is the GoConnect document for a voyage. Master Bill links it in **Vessel Schedule**.
- **Auto-link Vessel Schedule** finds a schedule by voyage number and IMO, or creates one from the bill (vessel, shipping line, load and discharge ports, scheduled departure and arrival).
- **Auto-Update from Vessel Schedule** keeps voyage status, ETA, ATD, ATA, and position in step with that schedule.
- **Refresh voyage status** calls `goconnect.api.sea.sync_voyage_data`. The voyage tracker is license-gated. Without the license, or without the app, the button explains what is missing.
- Voyage status values written back: Scheduled, At Origin, Departed, In Transit, Arrived, At Destination, Delayed, Cancelled. Position fields include latitude, longitude, speed in knots, last update, and the provider name.
- The Sea Shipment dashboard map uses `goconnect.api.sea.get_vessel_position_for_map`. The vessel is taken from the main sea leg’s Vessel master (MMSI / IMO), with a fallback leg when that lookup misses.

### 3.2 Air — schedules and live flights

- Schedule connectors, the aggregator, and the flight jobs live in `goconnect.flight`. CargoNext keeps thin call-throughs so Air Shipment, Master Air Waybill, and the dashboards do not change.
- **GoConnect Settings ▸ Flight** is linked from the Air Freight workspace (**GoConnect Settings (Flight)**).
- Schedule sources behind the aggregator: OpenSky, AviationStack, and Aviation Edge.
- Live positions for operational flights (a Flight Schedule on a Master Air Waybill that an Air Shipment still references):
  - OpenSky, when **OpenSky** is enabled on the Flight tab. One `/states/all` pull covers the callsigns on screen.
  - Then the public ADS-B aggregators adsb.lol and adsb.fi.
- The Air Freight operations map marks each fix live, stale (older than 60 minutes with no new state), or with no position. Callsigns are matched from IATA flight numbers and ICAO designators.
- Jobs still registered from CargoNext, executed by GoConnect:
  - Every 10 minutes: sync active flights.
  - Hourly: write flight status back onto air jobs.
  - Daily: drop old schedules and old sync logs.
- Search by origin, destination, and date goes through the GoConnect flight aggregator.

### 3.3 Land — vehicle telematics

- Provider clients and the ingest tick live in `goconnect.land`. CargoNext still owns **Telematics Provider**, **Transport Vehicle**, and **Transport Settings → Default Telematics Provider**.
- Provider types: Remora (SOAP), Traccar, Wialon, Geotab, Samsara, and Custom.
- A vehicle stores the provider, the external device id, and the last fix (`last_telematics_lat`, `last_telematics_lon`, `last_telematics_ts`). The vehicle form can open that point on a map.
- The same last fix is what the transport portal and the transport job detail page show the customer.
- Poll interval remains **Telematics Poll Interval (min)** on Transport Settings.

### 3.4 What you install

- Install the `goconnect` app on the site, then set providers under GoConnect Settings (Vessel, Flight, and the land providers used by Telematics Provider).
- Vessel voyage tracking checks the GoConnect license before a live pull.
- CargoNext reaches GoConnect through `logistics.utils.goconnect` for Master Bill voyage actions, so a missing app returns a message instead of an import error. Flight and land call-throughs import `goconnect` directly; those paths need the app present.

---

## 4. CargoNext AI

CargoNext AI is the separate Frappe app `cargonext_ai`. A CargoNext site that also runs GoConnect has reported it at **0.1.0**. In support it is labelled **CARGO AI**. Its code is not in the logistics repository, so this note lists only the behaviour this app can confirm.

- It is installed beside logistics and GoConnect. It is not a module inside `modules.txt`.
- The assistant shows a **disclaimer** on its desk surface.
- A repeated disclaimer was reported against CargoNext and closed with the instruction to track it on the `cargonext_ai` app ([#1109](https://github.com/agilasoft/logistics/issues/1109)). Fixes for the assistant belong in that app.
- What the assistant is allowed to read, draft, or submit is defined in `cargonext_ai`. Those skills are not listed here, because this repository does not contain them.

---

## 5. How to read these notes

- Section 2 is the recorded Bessel scope.
- Section 3 is GoConnect behaviour already called from this app.
- Section 4 is CargoNext AI as far as this app can see it.
- v1 Astraea operations (sea, air, transport, customs, warehousing, pricing, job costing, credit) remain the base. See [CargoNext v1 — Release Notes](welcome/release-notes-v1).

**Support:** info@agilasoft.com · [www.agilasoft.com](https://www.agilasoft.com)

---

<!-- wiki-field-reference:start -->

## Complete field reference

_List notes only. Voyage fields on the bill are on [Master Bill](welcome/master-bill). Vessel tracking setup is described on [Sea Freight Settings](welcome/sea-freight-settings). Vehicle telematics fields are on [Transport Settings](welcome/transport-settings)._

<!-- wiki-field-reference:end -->
