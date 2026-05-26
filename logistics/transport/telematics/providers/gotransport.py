from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import requests

from .base import TelematicsProvider, Position, Event, Temperature, CanSnapshot

_LOG = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _parse_dt(value: Any) -> Optional[datetime]:
    """
    Parse a timestamp coming from gotransport.api.

    Accepts ISO 8601 strings (with/without ``Z``), MySQL ``YYYY-MM-DD HH:MM:SS``
    strings, ``datetime`` instances, or numeric epoch seconds/milliseconds.
    Returns a tz-aware UTC datetime, or ``None`` if not parseable.
    """
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:  # ms → s
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.lstrip("-").isdigit():
            return _parse_dt(int(s))
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _f(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "null"):
            return None
        return float(value)
    except Exception:
        return None


def _get(d: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """First non-empty value among ``keys`` (case-insensitive fallback)."""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    lower = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, ""):
            return v
    return default


def _iso_z(dt: Optional[datetime]) -> Optional[str]:
    """Render a tz-aware datetime as ``YYYY-MM-DDTHH:MM:SSZ`` for the API."""
    if dt is None:
        return None
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #

class GoTransportProvider(TelematicsProvider):
    """
    Go Transport mobile telematics provider (Agilasoft Cloud Technologies Inc.).

    The Go Transport mobile app POSTs every event to ``gotransport.api.ingest_event``
    on the same Frappe bench (or on a remote site when ``base_url`` is set).
    This provider polls ``gotransport.api.get_latest_positions`` on the
    cadence configured in *Transport Settings → Telematics* and feeds the
    standard logistics telematics pipeline (ETA, Auto-Arrival, Auto-Departure).

    Wire contract (server returns)::

        {
          "positions": [
            {
              "vehicle":                "TV-0007",          # already resolved
              "gotransport_device":     "GT-v1-...",        # stable device id
              "telematics_external_id": "ABC-1234",         # legacy fallback
              "latitude":  14.5547,
              "longitude": 121.0244,
              "accuracy_m":  6.4,
              "speed_mps":   12.3,
              "heading_deg": 87.0,
              "recorded_at": "2026-05-25 08:00:00"
            },
            ...
          ]
        }

    Vehicle resolution priority (matches the server-side resolver):
        gotransport_device → telematics_external_id → license_plate → name

    Config (Telematics Provider doc):
      * ``position_method``   — defaults to ``gotransport.api.get_latest_positions``
      * ``base_url``          — empty for in-site call; set for remote site
      * ``api_key``           — Frappe API key (remote only)
      * ``api_secret``        — Frappe API secret (remote only;
                                stored on the Go Transport tab as
                                ``gotransport_api_secret``)
      * ``request_timeout_sec`` / ``timeout`` — default 15 if 0/None
    """

    DEFAULT_POSITION_METHOD = "gotransport.api.get_latest_positions"
    DEFAULT_TIMEOUT_SEC = 15
    DEFAULT_LIMIT = 500

    # ----------------------------------------------------------------- init

    def __init__(self, conf: Dict[str, Any]):
        self.conf = conf or {}

        self.position_method = (
            self.conf.get("position_method")
            or self.conf.get("gotransport_position_method")
            or self.DEFAULT_POSITION_METHOD
        ).strip()

        self.base = (self.conf.get("base_url") or "").rstrip("/")
        self.api_key = (self.conf.get("api_key") or "").strip()
        self.api_secret = (
            self.conf.get("api_secret")
            or self.conf.get("gotransport_api_secret")
            or ""
        ).strip()

        # Treat 0 / None / negative as "use default" — Frappe's Int field
        # delivers 0 when the user never typed a value.
        raw_timeout = self.conf.get("request_timeout_sec") or self.conf.get("timeout") or 0
        try:
            timeout = float(raw_timeout)
        except (TypeError, ValueError):
            timeout = 0
        self.timeout = timeout if timeout > 0 else float(self.DEFAULT_TIMEOUT_SEC)

        self.provider_docname = (self.conf.get("provider_docname") or self.conf.get("name") or "").strip()
        # ``resolve_vehicle_provider`` enriches the conf with these when the
        # poll is per-vehicle; the bulk ingest doesn't set them.
        self.external_id = (self.conf.get("external_id") or "").strip()
        self.vehicle_name = (self.conf.get("vehicle_name") or "").strip()

        _LOG.info(
            "GoTransport init mode=%s method=%s base=%s timeout=%.0f",
            "http" if self.base else "local",
            self.position_method,
            self.base or "-",
            self.timeout,
        )

    # ------------------------------------------------------------------ call

    def _call_local(self, since: Optional[str], limit: int) -> Any:
        """Invoke the whitelisted method in-process via ``frappe.get_attr``."""
        try:
            import frappe  # local import: tests may exercise this w/o Frappe
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"frappe not available for in-site call: {e}") from e

        try:
            fn = frappe.get_attr(self.position_method)
        except Exception as e:
            raise RuntimeError(
                f"Could not resolve {self.position_method!r} "
                f"(is the 'gotransport' app installed on this bench?): {e}"
            ) from e

        kwargs: Dict[str, Any] = {"limit": limit}
        if since:
            kwargs["since"] = since

        try:
            return fn(**kwargs)
        except TypeError:
            # Older signatures may not accept since/limit kwargs.
            try:
                return fn()
            except Exception as e:
                raise RuntimeError(f"{self.position_method} raised: {e}") from e
        except Exception as e:
            raise RuntimeError(f"{self.position_method} raised: {e}") from e

    def _call_http(self, since: Optional[str], limit: int) -> Any:
        """Invoke the whitelisted method over HTTP against a remote site."""
        url = f"{self.base}/api/method/{self.position_method}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key and self.api_secret:
            headers["Authorization"] = f"token {self.api_key}:{self.api_secret}"
        elif self.api_key:
            headers["Authorization"] = f"token {self.api_key}"

        body: Dict[str, Any] = {"limit": limit}
        if since:
            body["since"] = since

        try:
            r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise RuntimeError(f"GoTransport poll request failed @ {url}: {e}") from e

        if r.status_code >= 400:
            snippet = (r.text or "")[:300].replace("\n", " ")
            raise RuntimeError(f"GoTransport poll HTTP {r.status_code} @ {url}: {snippet}")

        try:
            payload = r.json()
        except ValueError as e:
            snippet = (r.text or "")[:200].replace("\n", " ")
            raise RuntimeError(f"GoTransport poll returned non-JSON: {snippet}") from e

        # Frappe wraps whitelisted method responses as {"message": <value>}
        if isinstance(payload, dict) and "message" in payload:
            payload = payload["message"]
        return payload

    def _call(self, since: Optional[str], limit: int) -> List[Dict[str, Any]]:
        raw = self._call_http(since, limit) if self.base else self._call_local(since, limit)
        return _coerce_rows(raw)

    # ------------------------------------------------------------- mapping

    def _vehicle_lookup(self) -> Dict[str, str]:
        """
        Build ``{any-known-identifier -> Transport Vehicle name}`` so we
        can resolve a row to a vehicle whether the gotransport server
        returns the resolved name, the device id, or the legacy external id.

        Keys included for each vehicle:
          * the vehicle's own ``name`` (e.g. ``"TV-0007"``)
          * ``gotransport_device``        (e.g. ``"GT-v1-..."``)
          * ``telematics_external_id``    (e.g. ``"ABC-1234"``)

        Restricted to vehicles bound to this provider when
        ``provider_docname`` is known; otherwise scans the full table.
        """
        try:
            import frappe
        except Exception:  # pragma: no cover
            return {}

        filters: Dict[str, Any] = {}
        if self.provider_docname:
            filters["telematics_provider"] = self.provider_docname

        try:
            rows = frappe.get_all(
                "Transport Vehicle",
                filters=filters,
                fields=["name", "telematics_external_id", "gotransport_device"],
            )
        except Exception as e:
            _LOG.warning("GoTransport: could not load Transport Vehicle map: %s", e)
            return {}

        out: Dict[str, str] = {}
        for r in rows:
            name = str(r.get("name") or "").strip()
            if not name:
                continue
            out[name] = name
            for key in ("gotransport_device", "telematics_external_id"):
                v = (r.get(key) or "")
                v = str(v).strip()
                if v:
                    out.setdefault(v, name)
        return out

    def _row_external_id(self, row: Dict[str, Any], lookup: Dict[str, str]) -> Optional[str]:
        """
        Resolve a server-returned row to the identifier the logistics
        ingest pipeline will use (``Position.external_id``). Returns the
        Transport Vehicle name when possible, so the extended
        ``ingest._vehicles_with_mapping`` can look it up directly.
        """
        for k in ("vehicle", "name", "gotransport_device", "telematics_external_id", "device_id"):
            v = row.get(k)
            if v in (None, ""):
                continue
            mapped = lookup.get(str(v))
            if mapped:
                return mapped
        # Per-vehicle hint when ``resolve_vehicle_provider`` set us up.
        if self.external_id:
            return self.external_id
        return None

    @staticmethod
    def _map_position(row: Dict[str, Any], external_id: str) -> Optional[Position]:
        ts = _parse_dt(_get(row, "recorded_at", "timestamp", "ts"))
        lat = _f(_get(row, "latitude", "lat"))
        lon = _f(_get(row, "longitude", "lon", "lng"))
        if ts is None or lat is None or lon is None:
            return None

        # Mobile reports SI units (m/s). Convert to km/h for downstream
        # callers — the rest of the telematics pipeline assumes km/h.
        speed_ms = _f(_get(row, "speed_mps", "speed"))
        speed_kph = speed_ms * 3.6 if speed_ms is not None else None

        return {
            "external_id": external_id,
            "ts": ts,
            "lat": lat,
            "lon": lon,
            "speed_kph": speed_kph,
            "ignition": None,
            "odometer_km": None,
            "raw": row,
        }

    # ------------------------------------------------------------- fetchers

    def fetch_latest_positions(self, since: Optional[datetime] = None) -> Iterable[Position]:
        since_str = _iso_z(since) if isinstance(since, datetime) else (since or None)

        try:
            rows = self._call(since_str, self.DEFAULT_LIMIT)
        except RuntimeError as e:
            _LOG.warning("GoTransport fetch_latest_positions failed: %s", e)
            return

        if not rows:
            return

        lookup = self._vehicle_lookup()

        for row in rows:
            ext = self._row_external_id(row, lookup)
            if not ext:
                _LOG.debug(
                    "GoTransport: row not bound to any Transport Vehicle, skipping: %s",
                    {k: row.get(k) for k in ("vehicle", "gotransport_device", "telematics_external_id")},
                )
                continue
            mapped = self._map_position(row, ext)
            if mapped:
                yield mapped

    # Non-position fan-out endpoints are intentionally empty — the Go
    # Transport mobile app handles capture / shift / leg events via its
    # own server-side hooks against dedicated DocTypes, so we don't
    # double-store them through the telematics pipeline.

    def fetch_events(self, since=None, until=None):
        return []

    def fetch_temperatures(self, since=None, until=None):
        return []

    def fetch_can(self, since=None, until=None):
        return []

    def fetch_latest_can_data(self, since=None):
        """
        The Go Transport mobile app has no OBD-II hardware (it's a phone).
        Return an empty iterable so callers that unconditionally invoke
        this (e.g. Transport Vehicle.get_latest_position,
        api_telematics_debug.debug_can_data) get a clean no-op instead of
        an AttributeError or a server-side traceback.
        """
        return []


# --------------------------------------------------------------------------- #
# Response coercion
# --------------------------------------------------------------------------- #

def _coerce_rows(payload: Any) -> List[Dict[str, Any]]:
    """
    Normalize ``gotransport.api.get_latest_positions`` payloads.

    Accepts the v2 contract::

        {"positions": [ {...}, ... ]}

    and the v1 contract::

        [ {...}, ... ]      |     {"data": [...]}     |     {"items": [...]}
    """
    if payload is None:
        return []
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except ValueError:
            return []
    if isinstance(payload, dict):
        for k in ("positions", "data", "items", "results", "records"):
            v = payload.get(k)
            if isinstance(v, list):
                payload = v
                break
        else:
            # Single-row dict
            return [payload] if payload else []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []
