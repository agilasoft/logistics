# GoTransport — Standalone Telematics Backend Brief

**Audience:** the AI agent (Cursor / Claude Code / etc.) building the `gotransport` server-side application.
**Status:** authoritative. Replaces any earlier brief that suggested `gotransport` should call into Frappe/CargoNext or live inside the `logistics` app.

---

## 0. One-paragraph summary

`gotransport` is a **standalone HTTP service** that does exactly two things:

1. **Ingests** GPS events POSTed by the *Go Transport* driver mobile app (one event per fix, batched is fine).
2. **Serves** the latest position per device over a polling endpoint that CargoNext (the `logistics.transport` module) calls every minute.

It owns its own database (devices + positions + idempotency keys). It does **not** call CargoNext. It does **not** know about `Transport Vehicle`, `Transport Order`, `Run Sheet`, `Telematics Position`, or any other CargoNext DocType. CargoNext owns vehicle ↔ device pairing and feeds the position stream into its own pipelines.

---

## 1. System boundary diagram (the only one that matters)

```
 ┌──────────────────────┐   POST events             ┌────────────────────────┐
 │  Go Transport mobile │ ───────────────────────▶ │      gotransport       │
 │       app            │                            │   (this service)       │
 │  (driver's phone)    │ ◀──────────────────────── │  POST /ingest_event    │
 │                      │   200 OK { received: N }  │  POST /get_latest_…    │
 └──────────┬───────────┘                            └───────────┬────────────┘
            │                                                    │
            │ POST set_value("Transport Vehicle",                │ poll
            │   <name>, "gotransport_device",                    │ /get_latest_positions
            │   "GT-v1-<uuid>")                                  │
            │ (uses Driver's Frappe API key)                     ▼
            │                                          ┌─────────────────────┐
            └────────────────────────────────────────▶ │      CargoNext      │
                                                       │  (logistics app)    │
                                                       │  poll = 1 min       │
                                                       └─────────────────────┘
```

- gotransport ↔ mobile: HTTPS, per-device bearer token.
- gotransport ↔ CargoNext: HTTPS, API key + secret (one pair, server-to-server).
- CargoNext ↔ mobile: Frappe REST (standard `/api/method/frappe.client.set_value` etc.), Driver's own key:secret.
- **No edge crosses from gotransport into CargoNext. Ever.**

---

## 2. Why this shape

- Other CargoNext telematics providers (`remora`, `traccar`, `wialon`, `geotab`, `samsara`) are also "polled remote services" — `gotransport` slots into the existing `TelematicsProvider` plug-in pattern with **zero coupling**.
- The provider client on CargoNext (`logistics/transport/telematics/providers/gotransport.py`) is already written and wired. It just needs a URL + key + secret.
- A standalone service can be deployed once and re-used by any number of CargoNext tenants; each tenant configures its own `Telematics Provider` record pointing at the same `gotransport` URL with its own API key.
- gotransport never needs a CargoNext schema; CargoNext upgrades don't break gotransport and vice-versa.

---

## 3. Tech stack choice

**Recommended:** Frappe app on its own bench/site (`gotransport.youcompany.com`).
Reasons: free API-key authentication, free admin UI for inspecting events, the mobile devs already know the `Authorization: token KEY:SECRET` pattern.

**Acceptable alternatives:** FastAPI + Postgres, NestJS + Postgres, anything that can serve the four JSON endpoints in §6 with the auth in §5. If you choose a non-Frappe stack, change the endpoint paths to `/api/v1/...` and document them.

The rest of this brief assumes Frappe. Adapt path names if you pick something else.

---

## 4. Data model

Three tables — nothing more.

### 4.1 `GoTransport Device`

| Field             | Type      | Notes                                                      |
| ----------------- | --------- | ---------------------------------------------------------- |
| `name` (PK)       | Data      | The device id — format `GT-v1-<uuid4>`                     |
| `platform`        | Select    | `Android` \| `iOS`                                         |
| `app_version`     | Data      | e.g. `1.4.2 (build 314)`                                   |
| `device_label`    | Data      | Human-readable phone label (`Driver Juan's S23`)           |
| `bearer_token`    | Password  | The token the mobile app sends in `Authorization: Bearer …`. Issued once at register, rotatable. |
| `registered_at`   | Datetime  | First POST to `register_device`                            |
| `last_seen_at`    | Datetime  | Updated on every `ingest_event` call                       |
| `enabled`         | Check     | Default 1. Server refuses ingest when 0.                   |

**No driver field. No vehicle field.** Pairing is CargoNext's concern (see §8).

### 4.2 `GoTransport Position`

| Field            | Type     | Notes                                       |
| ---------------- | -------- | ------------------------------------------- |
| `name` (PK)      | autoname | hash-based                                  |
| `device`         | Link     | → `GoTransport Device`                      |
| `event_id`       | Data     | Unique-with-device. Mobile-generated UUIDv4. Used for idempotency. |
| `recorded_at`    | Datetime | Indexed. UTC. Time the fix was taken on the phone. |
| `received_at`    | Datetime | Server-side receive time.                   |
| `latitude`       | Float(8) | WGS-84                                      |
| `longitude`      | Float(8) | WGS-84                                      |
| `accuracy_m`     | Float(2) | Nullable                                    |
| `speed_mps`      | Float(3) | **Meters/sec** — not km/h.                  |
| `heading_deg`    | Float(1) | 0–360                                       |
| `altitude_m`     | Float(2) | Nullable                                    |
| `battery_pct`    | Int      | Nullable, 0–100                             |
| `is_charging`    | Check    | Nullable, default null                      |
| `raw_payload`    | Long Text | Full original JSON the mobile sent (for forensics) |

**Indexes:**
- `UNIQUE(device, event_id)` — primary idempotency guard
- `(device, recorded_at DESC)` — drives `get_latest_positions`
- `(received_at)` — drives the pruning job

### 4.3 `GoTransport API Key` (optional but recommended)

Per CargoNext tenant. So you can revoke one tenant's poll access without disturbing another.

| Field          | Type     | Notes                                              |
| -------------- | -------- | -------------------------------------------------- |
| `name` (PK)    | autoname | e.g. `cargonext-prod`                              |
| `api_key`      | Data     | Public, sent in `Authorization`                    |
| `api_secret`   | Password | Hashed at rest if non-Frappe                       |
| `scopes`       | Select   | `read_positions` \| `read_positions,register_devices` |
| `enabled`      | Check    | Default 1                                          |
| `created_at`   | Datetime |                                                    |
| `last_used_at` | Datetime | Updated on each successful call                    |

If on Frappe you can just use the built-in user `api_key` + `api_secret` on a service user (e.g. `cargonext-poller@gotransport.local`).

---

## 5. Authentication

Two completely separate credential populations:

| Caller        | Header                                  | Verified against                |
| ------------- | --------------------------------------- | ------------------------------- |
| Mobile app    | `Authorization: Bearer <device.bearer_token>` | `GoTransport Device.bearer_token` |
| CargoNext     | `Authorization: token KEY:SECRET`       | `GoTransport API Key`           |

Rules:
- A mobile bearer token grants **only** `POST /ingest_event` for its own `device_id`.
- A CargoNext key grants **only** `POST /get_latest_positions` (and `register_device` if scoped).
- Reject every request that lacks the right credential **before** touching the database. Return `401`.
- Rate-limit aggressively — see §9.

---

## 6. HTTP API

Base path examples below assume Frappe. For non-Frappe, replace `/api/method/gotransport.api.<method>` with `/api/v1/<method>`.

### 6.1 `POST register_device` — mobile only, first launch

```http
POST /api/method/gotransport.api.register_device
Content-Type: application/json
```
```json
{
  "platform":     "Android",
  "app_version":  "1.4.2 (314)",
  "device_label": "Juan's Galaxy S23"
}
```
**Response 200**
```json
{
  "device_id":    "GT-v1-7f8a3c14-…",
  "bearer_token": "btk_live_b3kx9…"
}
```
- Generates a new `GT-v1-<uuid4>` id.
- Generates a high-entropy `bearer_token` (≥256 bits, base64url).
- Stores the device row. Sets `registered_at = now()`, `enabled = 1`.
- Token is returned **once** — never readable again. (Frappe `Password` field already enforces this.)
- Idempotency: if the mobile retries with the same `Idempotency-Key` header, return the previous response unchanged. (See §10.)

### 6.2 `POST ingest_event` — mobile only, batched

```http
POST /api/method/gotransport.api.ingest_event
Authorization: Bearer btk_live_b3kx9…
Content-Type: application/json
```
```json
{
  "device_id": "GT-v1-7f8a3c14-…",
  "events": [
    {
      "event_id":    "1d3c4f5a-…",
      "recorded_at": "2026-05-25T08:00:00Z",
      "latitude":    14.5547,
      "longitude":   121.0244,
      "accuracy_m":  6.4,
      "speed_mps":   12.3,
      "heading_deg": 87.0,
      "altitude_m":  18.5,
      "battery_pct": 73,
      "is_charging": false
    }
  ]
}
```
**Response 200**
```json
{ "accepted": 1, "duplicate": 0, "rejected": 0 }
```
**Rules:**
- `device_id` in body **must** equal the device the bearer token belongs to. Else `401`.
- For each event: insert into `GoTransport Position`. On unique violation of `(device, event_id)`, increment `duplicate` instead of `rejected`. Never error.
- Validate: `latitude ∈ [-90, 90]`, `longitude ∈ [-180, 180]`, `recorded_at` parseable, `recorded_at ≤ now() + 5min` (clock-skew tolerance). Bad rows go into `rejected` count but the response stays `200`.
- Update `device.last_seen_at = now()`, `device.app_version = …` (if changed).
- Cap batch size at **500** events; if more, accept the first 500 and return `accepted < len(events)` so the mobile can retry the tail.
- Commit per batch, not per event.

### 6.3 `POST get_latest_positions` — CargoNext only

```http
POST /api/method/gotransport.api.get_latest_positions
Authorization: token KEY:SECRET
Content-Type: application/json
```
```json
{
  "since": "2026-05-25T07:59:00Z",   // optional; ISO-8601 UTC
  "limit": 500                        // optional; default 500, max 2000
}
```
**Response 200** — **this exact envelope, do not break it:**
```json
{
  "positions": [
    {
      "gotransport_device": "GT-v1-7f8a3c14-…",
      "recorded_at":        "2026-05-25T08:00:00Z",
      "latitude":           14.5547,
      "longitude":          121.0244,
      "accuracy_m":         6.4,
      "speed_mps":          12.3,
      "heading_deg":        87.0
    }
  ]
}
```
**Rules:**
- Return the **single most recent** position per device whose `received_at > since` (or whose `received_at` is unfiltered when `since` omitted).
- If no rows match, return `{"positions": []}` and `200`. Don't 404.
- Order doesn't matter to CargoNext but recommended: most-recent first.
- The fields above are the only ones CargoNext reads today. You can add more (e.g. `accuracy_m`, `altitude_m`) and CargoNext will ignore them. You may **not** rename any of them.
- **Do not** include a `vehicle` field — CargoNext does device → vehicle resolution itself via `Transport Vehicle.gotransport_device`.
- Cap at `limit` rows.

### 6.4 `POST rotate_bearer_token` — mobile, optional

For when a phone is lost or the user reinstalls. Mobile authenticates with the old token, gets back a new one. Old one is invalidated immediately.

### 6.5 Liveness / readiness

- `GET /api/method/gotransport.api.ping` → `{"pong": true, "version": "<git_sha>"}` — no auth.
- Used by load balancers and by CargoNext's admin smoke test.

---

## 7. Idempotency

Three layers:

1. **`(device, event_id)` unique constraint** on `GoTransport Position` — handles replays of the same fix.
2. **`Idempotency-Key` header on `register_device`** — same key returns the same `device_id`+`bearer_token` for 24h. Store keys in Redis (TTL 86 400 s).
3. **No idempotency needed on `get_latest_positions`** — it's a pure read.

---

## 8. What gotransport does NOT do

Spell these out in the README so future maintainers don't slip:

- ❌ Does not pair phones to vehicles. The mobile app writes `Transport Vehicle.gotransport_device` directly against CargoNext using the Driver's Frappe API key. gotransport never sees that field.
- ❌ Does not know which driver owns which device. (CargoNext knows; the mobile app knows; gotransport doesn't need to.)
- ❌ Does not push to CargoNext. CargoNext **polls** gotransport. If real-time push is ever desired, add a webhook to a new endpoint owned by CargoNext — but that's a future epic, not v1.
- ❌ Does not call any Frappe / CargoNext function or DocType.
- ❌ Does not store vehicle, route, customer, run-sheet, driver, or order data. Just device + position.

---

## 9. Rate limiting & abuse control

| Endpoint               | Limit                                   |
| ---------------------- | --------------------------------------- |
| `register_device`      | 5 / IP / hour, 1 / Idempotency-Key      |
| `ingest_event`         | 600 / device / hour (= 1 fix every 6 s) |
| `get_latest_positions` | 120 / API key / minute (= every 0.5 s)  |
| `rotate_bearer_token`  | 3 / device / hour                       |
| `ping`                 | unlimited                               |

Implement with Frappe's existing rate-limit decorator if available, else a Redis token bucket.

---

## 10. Retention / housekeeping

A scheduled job (Frappe `scheduler_events.cron`):

- Every 15 minutes: prune `GoTransport Position` rows where `received_at < now() - 90 days`. Configurable in a `GoTransport Settings` Single doctype (default 90).
- Every 5 minutes: mark `GoTransport Device.enabled = 0` for devices whose `last_seen_at < now() - 30 days`. (Configurable.)
- Daily: rotate expired Idempotency-Key entries in Redis. (TTL handles this automatically; the daily job just logs counts.)

---

## 11. Observability

- Structured JSON logs to stdout for every API call: `endpoint`, `caller_kind` (`device`/`tenant`), `caller_id` (device_id or api_key name), `status_code`, `latency_ms`, `accepted/duplicate/rejected` if applicable.
- Counter metrics (Prometheus or `frappe.metrics` if you have it):
  - `gotransport_events_received_total{result="accepted|duplicate|rejected"}`
  - `gotransport_devices_active_24h`
  - `gotransport_positions_poll_seconds`
- Sentry / Frappe error log for any 5xx.

---

## 12. Deployment

- DNS: `gotransport.<yourcompany>.com` (or shared with CargoNext on a path prefix — but separate subdomain is cleaner).
- TLS: required. No HTTP. No mixed.
- Service user on CargoNext side issues one API key per CargoNext site:
  - `cargonext-prod`        → `read_positions`
  - `cargonext-staging`     → `read_positions`
  - revocable independently.

---

## 13. How CargoNext consumes this (read-only — already done)

You don't need to touch this section; it's here so you know what fields and shapes CargoNext expects so you don't drift.

CargoNext side already has:

- `logistics/transport/telematics/providers/gotransport.py` — `GoTransportProvider` HTTP client. Already handles the envelope in §6.3, units (`speed_mps → speed_kph` × 3.6), `recorded_at` parsing, optional `accuracy_m` / `heading_deg`.
- Provider record: `Telematics Provider` doc with:
  - `provider_type = GOTRANSPORT`
  - `base_url = https://gotransport.<yourcompany>.com` (leave empty only if you choose to deploy gotransport as a Frappe app on the **same** bench as CargoNext — then it uses `frappe.get_attr` instead of HTTP. Not recommended for prod.)
  - `api_key`, `gotransport_api_secret` — the API key pair you minted in §4.3
  - `gotransport_position_method = gotransport.api.get_latest_positions` (Frappe) or your `/api/v1/get_latest_positions` path
  - `request_timeout_sec = 15`
- `Transport Vehicle.gotransport_device` (Custom Field, length 80, permlevel 1, indexed, in standard filter) — pairing target.
- Driver role has read+write at permlevel 1 on Transport Vehicle so the mobile pairing call works with the Driver's own API key.
- Scheduler polls every minute via `Transport Settings.telematics_poll_interval_min = 1`.
- `default_telematics_provider = goTransport` so any newly created vehicle without an explicit provider falls through to GoTransport.

Therefore: when the mobile app POSTs an event to gotransport, then within ≤1 minute CargoNext polls, resolves `gotransport_device` → `Transport Vehicle`, and writes a `Telematics Position` row → drives Auto-Arrival, Auto-Departure, ETA, etc.

---

## 14. Verification cookbook

Once gotransport is live, the agent should be able to walk through all of these end-to-end.

### 14.1 Mint a device + token

```bash
curl -sX POST https://gotransport.example.com/api/method/gotransport.api.register_device \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: 11111111-1111-1111-1111-111111111111' \
  -d '{"platform":"Android","app_version":"1.0.0","device_label":"smoke-1"}'
# → {"device_id":"GT-v1-...","bearer_token":"btk_live_..."}
```

### 14.2 Push a fix

```bash
curl -sX POST https://gotransport.example.com/api/method/gotransport.api.ingest_event \
  -H 'Authorization: Bearer btk_live_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "device_id":"GT-v1-...",
    "events":[{
      "event_id":"22222222-2222-2222-2222-222222222222",
      "recorded_at":"2026-05-25T08:00:00Z",
      "latitude":14.5547,"longitude":121.0244,
      "accuracy_m":6.4,"speed_mps":12.3,"heading_deg":87
    }]
  }'
# → {"accepted":1,"duplicate":0,"rejected":0}
```

Run the same `curl` twice — second call must return `{"accepted":0,"duplicate":1,"rejected":0}`.

### 14.3 Poll from CargoNext's perspective

```bash
curl -sX POST https://gotransport.example.com/api/method/gotransport.api.get_latest_positions \
  -H 'Authorization: token CARGONEXT_KEY:CARGONEXT_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"limit":50}'
# → {"positions":[{"gotransport_device":"GT-v1-...","recorded_at":"...", ...}]}
```

### 14.4 Pair the device to a vehicle (CargoNext side, not gotransport)

```bash
curl -sX PUT https://logistics.agilasoft.com/api/method/frappe.client.set_value \
  -H 'Authorization: token DRIVER_KEY:DRIVER_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"doctype":"Transport Vehicle","name":"TV-0007","fieldname":"gotransport_device","value":"GT-v1-..."}'
```

### 14.5 Confirm the loop closed

Within 60 s, a `Telematics Position` row should appear on CargoNext:

```bash
bench --site logistics.agilasoft.com execute \
  frappe.db.get_all --kwargs '{"doctype":"Telematics Position","filters":{"vehicle":"TV-0007"},"order_by":"ts desc","limit":1}'
```

If yes — integration is live.

---

## 15. Definition of done

Tick every box before declaring v1 shipped.

- [ ] All four POST endpoints + `ping` implemented, tested, documented (OpenAPI / Postman collection).
- [ ] Bearer-token auth on mobile endpoints; key:secret auth on tenant endpoint. 401 on missing/bad/wrong-scope credentials.
- [ ] `(device, event_id)` unique constraint enforced at DB level (not just app level).
- [ ] `get_latest_positions` returns one row per device, most-recent, in the envelope of §6.3 with exact field names.
- [ ] Rate limits in place per §9.
- [ ] Pruning + dormancy jobs scheduled per §10.
- [ ] Structured logs + Prometheus metrics per §11.
- [ ] cURL recipes in §14 all succeed against the deployed instance.
- [ ] CargoNext's scheduler shows successful `Transport/Telematics` poll runs (no `App gotransport is not installed`, no `401`, no `timeout`) for at least 30 consecutive minutes.
- [ ] README documents §8 (the "does NOT do" list) prominently. The system survives only as long as that boundary survives.

---

## 16. Out-of-scope (intentionally)

- Web/desktop dashboards for fleet visualization. (CargoNext does this.)
- Geofencing, ETA, route planning. (CargoNext does this.)
- Driver / customer / dispatch UIs. (CargoNext does this.)
- Push notifications to drivers. (Mobile app + Firebase, separate concern.)
- Storing trip / journey aggregates. (Belongs in CargoNext's `Run Sheet`.)
- HOS (hours-of-service) compliance. (Future, in CargoNext.)

If any of these creep into a PR, push back: gotransport's job is **events in, latest positions out**. Keep it boring.
