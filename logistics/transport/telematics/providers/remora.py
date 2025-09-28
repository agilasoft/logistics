# logistics/transport/telematics/providers/remora.py
from __future__ import annotations

import logging
import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

try:
    import xmltodict  # SOAP XML → dict
    _HAS_XMLTODICT = True
except Exception:
    _HAS_XMLTODICT = False

_LOG = logging.getLogger(__name__)


class RemoraProvider:
    """
    EvoGPS Export API (REMORA) SOAP client with terminal debug mode.

    Config (Telematics Provider row or dict passed to __init__):
      - username (required)
      - password (required)
      - soap_endpoint_override  (recommended), e.g.:
          https://api.evogps.com/Services/Data/ExportApiDataService.svc/basicHttp
      - soap_version: "SOAP11" | "SOAP12"  (default SOAP11; basicHttp in WSDL)
      - base_url: optional (used for logs/discovery only)
      - request_timeout_sec | timeout (default 20)
      - debug: 0/1  (prints request + response to terminal/logs when 1)
    """

    # Target namespace from WSDL
    NS = "Evogps.Centrack.Data.Service.ExportApi"
    SOAP11_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
    SOAP12_ENV = "http://www.w3.org/2003/05/soap-envelope"

    # Document-literal actions (for SOAPAction / content-type)
    ACTIONS = {
        "GetVersionInfo": f"{NS}/DataService/GetVersionInfo",
        "GetDevices": f"{NS}/DataService/GetDevices",
        "GetDrivers": f"{NS}/DataService/GetDrivers",
        "GetPositions": f"{NS}/DataService/GetPositions",
        "GetPositionsByInterval": f"{NS}/DataService/GetPositionsByInterval",
        "GetHarshEventsByInterval": f"{NS}/DataService/GetHarshEventsByInterval",
        "GetGeoShapeInfringementsByInterval": f"{NS}/DataService/GetGeoShapeInfringementsByInterval",
        "GetOdometers": f"{NS}/DataService/GetOdometers",
    }

    def __init__(self, config: Dict[str, Any]):
        self.username = (config.get("username") or "").strip()
        self.password = (config.get("password") or "").strip()
        self.timeout  = float(config.get("request_timeout_sec") or config.get("timeout") or 20)
        self.debug    = bool(config.get("debug") or 0)

        if not self.username or not self.password:
            raise ValueError("REMORA username/password not configured")

        endpoint = (config.get("soap_endpoint_override") or "").strip()
        if not endpoint:
            # Default to HTTPS + basicHttp (SOAP 1.1) per WSDL
            endpoint = "https://api.evogps.com/Services/Data/ExportApiDataService.svc/basicHttp"
        self.endpoint = endpoint.rstrip("/")

        ver = (config.get("soap_version") or "SOAP11").upper()
        self.soap_version = "SOAP12" if ver == "SOAP12" else "SOAP11"

        self.base_url = (config.get("base_url") or "").strip()

        _LOG.info("REMORA init endpoint=%s soap=%s timeout=%.0f debug=%s",
                  self.endpoint, self.soap_version, self.timeout, int(self.debug))

    # --------------------------
    # SOAP helpers + fault parsing
    # --------------------------

    def _headers(self, soap_action: str) -> Dict[str, str]:
        if self.soap_version == "SOAP12":
            return {"Content-Type": f'application/soap+xml; charset=utf-8; action="{soap_action}"'}
        return {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{soap_action}"'}

    def _envelope(self, op: str, body_xml: str) -> str:
        env = self.SOAP12_ENV if self.soap_version == "SOAP12" else self.SOAP11_ENV
        # document/literal — operation element in target namespace; children unqualified
        return (
            f'<?xml version="1.0" encoding="utf-8"?>'
            f'<soapenv:Envelope xmlns:soapenv="{env}">'
            f'  <soapenv:Body>'
            f'    <ns:{op} xmlns:ns="{self.NS}">{body_xml}</ns:{op}>'
            f'  </soapenv:Body>'
            f'</soapenv:Envelope>'
        )

    def _post_once(self, url: str, xml: str, headers: Dict[str, str]) -> requests.Response:
        return requests.post(url, data=xml.encode("utf-8"), headers=headers, timeout=self.timeout)

    def _parse_soap_fault(self, text: str) -> Optional[str]:
        if not _HAS_XMLTODICT:
            return None
        try:
            d = xmltodict.parse(text)
        except Exception:
            return None
        env = d.get("s:Envelope") or d.get("soap:Envelope") or d.get("Envelope") or {}
        body = env.get("s:Body") or env.get("soap:Body") or env.get("Body") or {}
        fault = body.get("s:Fault") or body.get("soap:Fault") or body.get("Fault")
        if not fault:
            return None
        code = fault.get("faultcode") or (fault.get("Code") or {}).get("Value")
        string = fault.get("faultstring") or (fault.get("Reason") or {}).get("Text")
        detail = fault.get("detail") or fault.get("Detail")
        bits = []
        if code: bits.append(f"faultcode={code}")
        if string: bits.append(f"faultstring={string}")
        if isinstance(detail, dict) and detail:
            bits.append(f"detail={list(detail.keys())}")
        return " | ".join(bits) if bits else "SOAP Fault"

    def _call(self, op: str, body_xml: str) -> Dict[str, Any]:
        if not _HAS_XMLTODICT:
            raise RuntimeError("xmltodict not installed; cannot parse SOAP XML. Install: bench pip install xmltodict")

        action = self.ACTIONS.get(op, f"{self.NS}/DataService/{op}")
        envelope = self._envelope(op, body_xml)
        headers  = self._headers(action)

        tried: List[Tuple[str, str]] = []
        candidates = [self.endpoint]

        # Help the first-run setup: try common variants if user pasted base svc URL
        variants = ["/basicHttp", "/wsHttp", "/soap", ""]
        if not any(self.endpoint.endswith(s) for s in variants):
            candidates.extend([self.endpoint + s for s in variants if self.endpoint + s not in candidates])

        last_err: Optional[str] = None
        for url in candidates:
            try:
                if self.debug:
                    print("\n=== REMORA SOAP REQUEST ===")
                    print("URL:", url)
                    print("SOAPAction:", action)
                    print(envelope)

                r = self._post_once(url, envelope, headers)
                ct = (r.headers.get("Content-Type") or "").lower()
                text = r.text or ""

                if self.debug:
                    print("\n=== REMORA SOAP RESPONSE ===")
                    print("HTTP:", r.status_code, r.reason, "| CT:", ct)
                    print(text[:2000])

                if r.status_code >= 400:
                    fault = None
                    if (ct.startswith("text/xml") or ct.startswith("application/soap+xml")) and text.strip().startswith("<"):
                        fault = self._parse_soap_fault(text)
                    if fault:
                        raise RuntimeError(f"{op} SOAP fault @ {url}: {fault}")
                    snippet = text[:200].replace("\n", " ")
                    raise RuntimeError(f"HTTP {r.status_code} @ {url} (ct={ct}) {snippet}")

                # Some proxies return HTML with 200 — guard it
                if "text/html" in ct or text.lstrip().lower().startswith("<!doctype html"):
                    raise RuntimeError(f"HTML page returned @ {url} (ct={ct})")

                return xmltodict.parse(text)
            except Exception as e:
                last_err = str(e)
                tried.append((url, last_err))
                continue

        tried_join = " | ".join([f"{u} -> {err}" for u, err in tried])
        hint = ("Check endpoint & version. Recommended: HTTPS basicHttp + SOAP11 "
                "(https://api.evogps.com/Services/Data/ExportApiDataService.svc/basicHttp)")
        raise RuntimeError(f"{op} failed after trying endpoints. {hint}. Details: {tried_join}")

    # --------------------------
    # Payload builders
    # --------------------------

    def _auth_body(self) -> str:
        # Per WSDL, children are userName/password (unqualified). Keeping ns: is fine in doc/lit.
        un = _xml_escape(self.username)
        pw = _xml_escape(self.password)
        return f"<ns:userName>{un}</ns:userName><ns:password>{pw}</ns:password>"

    # --------------------------
    # Operations (raw)
    # --------------------------

    def GetVersionInfo(self) -> Dict[str, Any]:
        doc = self._call("GetVersionInfo", self._auth_body())
        try:
            env = _dict_get_ci(doc, "Envelope")
            body = _dict_get_ci(env, "Body")
            resp = _dict_first_child_endswith(body, "Response")
            return resp or body or doc
        except Exception:
            return doc

    def GetDevices(self) -> List[Dict[str, Any]]:
        doc = self._call("GetDevices", self._auth_body())
        # WSDL: GetDevicesResponse / deviceList / Device
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResponse", "deviceList", "Device"])
        if out: return out
        # Some tenants flatten: GetDevicesResponse / Device
        return _extract_list(doc, ["Envelope", "Body", "GetDevicesResponse", "Device"])

    def GetDrivers(self) -> List[Dict[str, Any]]:
        doc = self._call("GetDrivers", self._auth_body())
        return _extract_list(doc, ["Envelope", "Body", "GetDriversResponse", "driverList", "Driver"])

    def GetPositions(self) -> List[Dict[str, Any]]:
        doc = self._call("GetPositions", self._auth_body())
        # WSDL: GetPositionsResponse / positionList / Position
        out = _extract_list(doc, ["Envelope", "Body", "GetPositionsResponse", "positionList", "Position"])  # ← canonical shape
        if out: return out
        # Fallbacks for older/variant shapes
        out = _extract_list(doc, ["Envelope", "Body", "GetPositionsResponse", "Position"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetPositionsResponse", "positions", "Position"])

    def GetPositionsByInterval(self, device_id: str, date_from: dt.datetime, date_to: dt.datetime) -> List[Dict[str, Any]]:
        xml = (
            f"{self._auth_body()}"
            f"<ns:deviceId>{_xml_escape(device_id)}</ns:deviceId>"
            f"<ns:datefrom>{_iso(date_from)}</ns:datefrom>"
            f"<ns:dateto>{_iso(date_to)}</ns:dateto>"
        )
        doc = self._call("GetPositionsByInterval", xml)
        # WSDL: GetPositionsByIntervalResponse / ArrayOfPosition / Position
        out = _extract_list(doc, ["Envelope", "Body", "GetPositionsByIntervalResponse", "Position"])
        if out: return out
        out = _extract_list(doc, ["Envelope", "Body", "GetPositionsByIntervalResponse", "ArrayOfPosition", "Position"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetPositionsByIntervalResponse", "positionList", "Position"])

    def GetHarshEventsByInterval(self, device_id: str, date_from: dt.datetime, date_to: dt.datetime) -> List[Dict[str, Any]]:
        xml = (
            f"{self._auth_body()}"
            f"<ns:deviceId>{_xml_escape(device_id)}</ns:deviceId>"
            f"<ns:datefrom>{_iso(date_from)}</ns:datefrom>"
            f"<ns:dateto>{_iso(date_to)}</ns:dateto>"
        )
        doc = self._call("GetHarshEventsByInterval", xml)
        out = _extract_list(doc, ["Envelope", "Body", "GetHarshEventsByIntervalResponse", "Event"])
        if out: return out
        out = _extract_list(doc, ["Envelope", "Body", "GetHarshEventsByIntervalResponse", "ExportHarshEventDto"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetHarshEventsByIntervalResponse", "ExportDrivingBehaviourDto"])

    def GetGeoShapeInfringementsByInterval(self, date_from: dt.datetime, date_to: dt.datetime) -> List[Dict[str, Any]]:
        xml = (
            f"{self._auth_body()}"
            f"<ns:datefrom>{_iso(date_from)}</ns:datefrom>"
            f"<ns:dateto>{_iso(date_to)}</ns:dateto>"
        )
        doc = self._call("GetGeoShapeInfringementsByInterval", xml)
        # WSDL: GetGeoShapeInfringementsByIntervalResponse / GeoShapeInfringement (list element name)
        out = _extract_list(doc, ["Envelope", "Body", "GetGeoShapeInfringementsByIntervalResponse", "GeoShapeInfringement"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetGeoShapeInfringementsByIntervalResponse", "ExportGeoshapeInfringementDto"])

    # --------------------------
    # Normalized helpers (for schedulers / callers)
    # --------------------------

    def fetch_latest_positions(self, since: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        for p in self.GetPositions():
            y = _pos_to_row(p)
            if y:
                yield y

    def fetch_harsh_events(self, device_id: str, start: dt.datetime, end: dt.datetime) -> Iterable[Dict[str, Any]]:
        for ev in self.GetHarshEventsByInterval(device_id, start, end):
            row = _harsh_to_row(ev)
            if row:
                yield row

    def fetch_geofence_events(self, start: dt.datetime, end: dt.datetime) -> Iterable[Dict[str, Any]]:
        for ev in self.GetGeoShapeInfringementsByInterval(start, end):
            row = _geo_to_row(ev)
            if row:
                yield row


# --------------------------
# Parsing utilities
# --------------------------

def _iso(d: dt.datetime) -> str:
    if not isinstance(d, dt.datetime):
        return str(d)
    if d.tzinfo:
        return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def _xml_escape(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def _extract_list(doc: Dict[str, Any], path: List[str]) -> List[Dict[str, Any]]:
    """
    Traverse xmltodict map with case-tolerant Envelope/Body and return a list.
    Raises if xmltodict is missing to avoid silent 'no response'.
    """
    if not _HAS_XMLTODICT:
        raise RuntimeError("xmltodict not installed; cannot parse SOAP XML. Install: bench pip install xmltodict")

    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict):
            return []
        if key in ("Envelope", "Body"):
            k = _first_key_like(cur, key)
            cur = cur.get(k, {})
        else:
            cur = cur.get(key, {})
    if isinstance(cur, list):
        return cur
    if isinstance(cur, dict) and cur:
        return [cur]
    return []


def _first_key_like(d: Dict[str, Any], short: str) -> str:
    for k in d.keys():
        if isinstance(k, str) and k.split(":")[-1] == short:
            return k
    return short


def _dict_get_ci(d: Dict[str, Any], short: str) -> Dict[str, Any]:
    if short in d:
        return d[short]
    for k, v in d.items():
        if isinstance(k, str) and k.split(":")[-1] == short:
            return v
    return {}


def _dict_first_child_endswith(d: Dict[str, Any], suffix: str) -> Optional[Dict[str, Any]]:
    for k, v in d.items():
        if isinstance(k, str) and k.endswith(suffix):
            return v
    return None


def _to_float(v: Any) -> Optional[float]:
    try:
        if v in (None, "", "null"):
            return None
        return float(v)
    except Exception:
        return None


def _pos_to_row(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Per WSDL: Position has deviceId, coordinate{latitude,longitude}, dateTime, lastCommunicationDateTime, heading, speed, ignitionState, mileage.
    # See: GetPositionsResponse/positionList/Position schema. :contentReference[oaicite:1]{index=1}
    dev = p.get("deviceId") or p.get("DeviceId") or p.get("deviceID")
    coord = p.get("coordinate") or p.get("Coordinate") or {}
    lat = _to_float(coord.get("latitude") if "latitude" in coord else coord.get("lat"))
    lon = _to_float(coord.get("longitude") if "longitude" in coord else coord.get("lon"))
    if dev and lat is not None and lon is not None:
        return {
            "device_id": str(dev),
            "latitude": lat,
            "longitude": lon,
            "speed_kph": _to_float(p.get("speed") or p.get("Speed")),
            "heading_deg": _to_float(p.get("heading") or p.get("Heading")),
            "ignition": ((p.get("ignitionState") or p.get("IgnitionState") or "") or "").upper() or None,
            "timestamp": p.get("dateTime") or p.get("DateTime") or p.get("lastCommunicationDateTime"),
            "raw": p,
        }
    return None


def _harsh_to_row(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coord = ev.get("coordinate") or ev.get("Coordinate") or {}
    return {
        "device_id": str(ev.get("deviceId") or ev.get("DeviceId") or ""),
        "latitude": _to_float(coord.get("latitude") if "latitude" in coord else coord.get("lat")),
        "longitude": _to_float(coord.get("longitude") if "longitude" in coord else coord.get("lon")),
        "event_type": ev.get("eventType") or ev.get("EventType"),
        "speed_kph": _to_float(ev.get("speed") or ev.get("Speed")),
        "timestamp": ev.get("dateTime") or ev.get("DateTime"),
        "raw": ev,
    }


def _geo_to_row(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return {
        "device_id": str(ev.get("deviceId") or ev.get("DeviceId") or ""),
        "geofence_name": ev.get("geoFenceName") or ev.get("GeoFenceName"),
        "start": ev.get("startDateTime") or ev.get("StartDateTime"),
        "end": ev.get("enddateTime") or ev.get("EndDateTime"),
        "raw": ev,
    }
