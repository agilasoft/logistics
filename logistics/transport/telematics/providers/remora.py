# logistics/transport/telematics/providers/remora.py
from __future__ import annotations

import logging
import datetime as dt
import time
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
        # Validate required configuration
        required_fields = ['username', 'password']
        missing = [f for f in required_fields if not config.get(f)]
        if missing:
            raise ValueError(f"Missing required REMORA configuration: {missing}")

        self.username = (config.get("username") or "").strip()
        self.password = (config.get("password") or "").strip()
        self.timeout  = float(config.get("request_timeout_sec") or config.get("timeout") or 20)
        self.debug    = bool(config.get("debug") or 0)
        
        # Debug capture for API responses
        self.debug_capture = config.get("debug_capture", False)
        self.debug_logs = [] if self.debug_capture else None

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

        # Validate timeout is reasonable
        if self.timeout < 5 or self.timeout > 300:
            _LOG.warning(f"REMORA timeout {self.timeout}s is outside recommended range (5-300s)")

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

    def _call(self, op: str, body_xml: str, max_retries: int = 3) -> Dict[str, Any]:
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
            for attempt in range(max_retries):
                try:
                    debug_info = {}
                    if self.debug or self.debug_capture:
                        debug_info = {
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "url": url,
                            "soap_action": action,
                            "envelope": envelope,
                            "headers": headers
                        }
                        if self.debug:
                            print(f"\n=== REMORA SOAP REQUEST (attempt {attempt + 1}/{max_retries}) ===")
                            print("URL:", url)
                            print("SOAPAction:", action)
                            print(envelope)

                    r = self._post_once(url, envelope, headers)
                    ct = (r.headers.get("Content-Type") or "").lower()
                    text = r.text or ""

                    if self.debug or self.debug_capture:
                        debug_info.update({
                            "http_status": r.status_code,
                            "http_reason": r.reason,
                            "content_type": ct,
                            "response_text": text,
                            "response_headers": dict(r.headers)
                        })
                        
                        if self.debug:
                            print(f"\n=== REMORA SOAP RESPONSE (attempt {attempt + 1}/{max_retries}) ===")
                            print("HTTP:", r.status_code, r.reason, "| CT:", ct)
                            print(text[:2000])
                        
                        if self.debug_capture:
                            self.debug_logs.append(debug_info)

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
                except (requests.ConnectionError, requests.Timeout) as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        _LOG.warning(f"Connection error for {op} @ {url}, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                        continue
                    else:
                        last_err = str(e)
                        tried.append((url, last_err))
                        break
                except Exception as e:
                    last_err = str(e)
                    tried.append((url, last_err))
                    break

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
        # WSDL: GetDevicesResponse / deviceList / Device (deviceList may be list of Device when multiple)
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResponse", "deviceList", "Device"])
        if out:
            return out
        # deviceList as direct list (no Device key)
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResponse", "deviceList"])
        if out:
            return out
        # Some tenants flatten: GetDevicesResponse / Device
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResponse", "Device"])
        if out:
            return out
        # CamelCase / alternate response names
        out = _extract_list(doc, ["Envelope", "Body", "getDevicesResponse", "deviceList", "Device"])
        if out:
            return out
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResult", "deviceList", "Device"])
        if out:
            return out
        out = _extract_list(doc, ["Envelope", "Body", "GetDevicesResult", "Device"])
        if out:
            return out
        # Last resort: recursively find any list of dicts that look like devices (have deviceId-like key)
        out = _find_device_list_in_doc(doc)
        if out:
            _LOG.info("REMORA GetDevices: used fallback device list (response structure differed from WSDL)")
            return out
        # Log response structure so we can add the correct path (no devices parsed)
        try:
            import json
            import frappe
            structure = _structure_summary(doc, max_depth=6)
            frappe.log_error(
                "Remora GetDevices returned 0 devices. Response structure (keys only):\n\n" + json.dumps(structure, indent=2),
                "Remora GetDevices - empty response structure"
            )
        except Exception:
            pass
        return []
    
    def get_device_id_by_name(self, device_name: str) -> Optional[str]:
        """
        Get device ID (UUID) by device name.
        Note: deviceId in Remora API is a UUID generated by the system,
        so you must call GetDevices first to get the mapping.
        
        Args:
            device_name: The name of the device to look up
            
        Returns:
            The device UUID if found, None otherwise
        """
        devices = self.GetDevices()
        for device in devices:
            # Try various field name variations for the device name
            name = (device.get("name") or device.get("Name") or 
                   device.get("deviceName") or device.get("DeviceName") or "")
            if str(name).strip().lower() == device_name.strip().lower():
                # Return the deviceId (UUID)
                return device.get("deviceId") or device.get("DeviceId") or device.get("deviceID")
        return None
    
    def get_all_device_mappings(self) -> Dict[str, str]:
        """
        Get a dictionary mapping device names to device IDs (UUIDs).
        Useful for batch operations where you need to look up multiple device IDs.
        
        Returns:
            Dictionary with device names as keys and UUIDs as values
        """
        devices = self.GetDevices()
        mapping = {}
        for device in devices:
            name = (device.get("name") or device.get("Name") or 
                   device.get("deviceName") or device.get("DeviceName") or "")
            device_id = device.get("deviceId") or device.get("DeviceId") or device.get("deviceID")
            if name and device_id:
                mapping[str(name).strip()] = str(device_id)
        return mapping
    
    def get_device_details(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive device details with all identifying information.
        Returns normalized device information including:
        - device_id (UUID): The unique device identifier
        - name: Device name
        - description: Device description
        - external_id: External reference ID (serial number, IMEI, etc.)
        - registration: Registration/license plate
        - make: Vehicle make
        - model: Vehicle model
        - vin: Vehicle Identification Number
        - imei: IMEI number
        - serial: Serial number
        - raw: Original raw device data
        
        Returns:
            List of dictionaries with normalized device details
        """
        devices = self.GetDevices()
        result = []
        
        for device in devices:
            device_info = {
                "device_id": _get_field(device, "deviceId", "DeviceId", "deviceID", "id", "Id", "ID"),
                "name": _get_field(device, "name", "Name", "deviceName", "DeviceName"),
                "description": _get_field(device, "description", "Description", "desc", "Desc"),
                "external_id": _get_field(device, "externalId", "ExternalId", "externalID", "ExternalID"),
                "registration": _get_field(device, "registration", "Registration", "regNumber", "RegNumber", "licensePlate", "LicensePlate"),
                "make": _get_field(device, "make", "Make", "manufacturer", "Manufacturer"),
                "model": _get_field(device, "model", "Model"),
                "vin": _get_field(device, "vin", "VIN", "Vin", "vehicleIdNumber", "VehicleIdNumber"),
                "imei": _get_field(device, "imei", "IMEI", "Imei"),
                "serial": _get_field(device, "serialNumber", "SerialNumber", "serial", "Serial"),
                "type": _get_field(device, "type", "Type", "deviceType", "DeviceType"),
                "status": _get_field(device, "status", "Status", "state", "State"),
                "raw": device
            }
            result.append(device_info)
        
        return result
    
    def print_device_details(self) -> None:
        """
        Print device details in a human-readable format.
        Useful for debugging and identifying devices.
        """
        devices = self.get_device_details()
        
        print(f"\n{'='*80}")
        print(f"Found {len(devices)} device(s)")
        print(f"{'='*80}\n")
        
        for i, device in enumerate(devices, 1):
            print(f"Device #{i}:")
            print(f"  Device ID (UUID):  {device['device_id']}")
            
            if device['name']:
                print(f"  Name:              {device['name']}")
            if device['description']:
                print(f"  Description:       {device['description']}")
            if device['external_id']:
                print(f"  External ID:       {device['external_id']}")
            if device['registration']:
                print(f"  Registration:      {device['registration']}")
            if device['make']:
                print(f"  Make:              {device['make']}")
            if device['model']:
                print(f"  Model:             {device['model']}")
            if device['vin']:
                print(f"  VIN:               {device['vin']}")
            if device['imei']:
                print(f"  IMEI:              {device['imei']}")
            if device['serial']:
                print(f"  Serial Number:     {device['serial']}")
            if device['type']:
                print(f"  Type:              {device['type']}")
            if device['status']:
                print(f"  Status:            {device['status']}")
            
            # Show all available fields from raw data
            print(f"  All Fields:        {', '.join(str(k) for k in device['raw'].keys() if device['raw'].get(k))}")
            print()

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
        """
        Get positions for a specific device within a time interval.
        
        Args:
            device_id: UUID of the device (get from GetDevices() or use get_device_id_by_name())
            date_from: Start datetime for the interval
            date_to: End datetime for the interval
            
        Returns:
            List of position records
        """
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
        """
        Get harsh driving events for a specific device within a time interval.
        
        Args:
            device_id: UUID of the device (get from GetDevices() or use get_device_id_by_name())
            date_from: Start datetime for the interval
            date_to: End datetime for the interval
            
        Returns:
            List of harsh event records
        """
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

    def GetCanData(self) -> List[Dict[str, Any]]:
        """
        Fetch latest CAN bus data for all devices configured on the account.

        WSDL: GetCanDataResponse / GetCanDataResult / ArrayOfCanData / CanData
        """
        doc = self._call("GetCanData", self._auth_body())
        # Canonical per WSDL
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataResponse", "GetCanDataResult", "CanData"])
        if out: return out
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataResponse", "GetCanDataResult", "ArrayOfCanData", "CanData"])
        if out: return out
        # Fallbacks (some deployments omit the *Result wrapper)
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataResponse", "CanData"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetCanDataResponse", "ArrayOfCanData", "CanData"])

    def GetCanDataByInterval(self, device_id: str, date_from: dt.datetime, date_to: dt.datetime) -> List[Dict[str, Any]]:
        """
        Fetch CAN bus data for a specific device within a time interval.

        WSDL: GetCanDataByIntervalResponse / GetCanDataByIntervalResult / ArrayOfCanData / CanData
        """
        xml = (
            f"{self._auth_body()}"
            f"<ns:deviceId>{_xml_escape(device_id)}</ns:deviceId>"
            f"<ns:datefrom>{_iso(date_from)}</ns:datefrom>"
            f"<ns:dateto>{_iso(date_to)}</ns:dateto>"
        )
        doc = self._call("GetCanDataByInterval", xml)
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataByIntervalResponse", "GetCanDataByIntervalResult", "CanData"])
        if out: return out
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataByIntervalResponse", "GetCanDataByIntervalResult", "ArrayOfCanData", "CanData"])
        if out: return out
        # Fallbacks
        out = _extract_list(doc, ["Envelope", "Body", "GetCanDataByIntervalResponse", "CanData"])
        if out: return out
        return _extract_list(doc, ["Envelope", "Body", "GetCanDataByIntervalResponse", "ArrayOfCanData", "CanData"])

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
                # Ensure external_id is properly mapped for interface compliance
                y['external_id'] = y.get('device_id')
                yield y
    
    def fetch_latest_can_data(self, since: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        """Fetch latest CAN data including fuel level"""
        for can_data in self.GetCanData():
            y = _can_to_row(can_data)
            if y:
                yield y

    def fetch_harsh_events(self, device_id: str, start: dt.datetime, end: dt.datetime) -> Iterable[Dict[str, Any]]:
        """
        Fetch harsh driving events for a specific device.
        
        Args:
            device_id: UUID of the device (get from GetDevices() or use get_device_id_by_name())
            start: Start datetime
            end: End datetime
            
        Yields:
            Normalized harsh event records
        """
        for ev in self.GetHarshEventsByInterval(device_id, start, end):
            row = _harsh_to_row(ev)
            if row:
                yield row

    def fetch_geofence_events(self, start: dt.datetime, end: dt.datetime) -> Iterable[Dict[str, Any]]:
        for ev in self.GetGeoShapeInfringementsByInterval(start, end):
            row = _geo_to_row(ev)
            if row:
                yield row

    def fetch_temperatures(self, since: dt.datetime, until: dt.datetime) -> Iterable[Dict[str, Any]]:
        """Fetch temperature sensor data from Remora API"""
        # Remora doesn't have a dedicated temperature endpoint, 
        # but we can extract temperature data from position data if available
        for device in self.GetDevices():
            device_id = _get_field(device, "deviceId", "DeviceId", "deviceID")
            if device_id:
                try:
                    for pos in self.GetPositionsByInterval(device_id, since, until):
                        temp_data = _extract_temperature_from_position(pos)
                        if temp_data:
                            yield temp_data
                except Exception:
                    # Skip devices that don't support temperature data
                    continue

    def fetch_can(self, since: dt.datetime, until: dt.datetime) -> Iterable[Dict[str, Any]]:
        """Fetch CAN bus data from Remora API"""
        # Remora doesn't have a dedicated CAN endpoint,
        # but we can extract CAN data from position data if available
        for device in self.GetDevices():
            device_id = _get_field(device, "deviceId", "DeviceId", "deviceID")
            if device_id:
                try:
                    for pos in self.GetPositionsByInterval(device_id, since, until):
                        can_data = _extract_can_from_position(pos)
                        if can_data:
                            yield can_data
                except Exception:
                    # Skip devices that don't support CAN data
                    continue

    def get_debug_logs(self) -> List[Dict[str, Any]]:
        """Get captured debug logs from API calls"""
        if self.debug_capture and self.debug_logs:
            return self.debug_logs.copy()
        return []


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


def _structure_summary(obj: Any, max_depth: int = 6, depth: int = 0) -> Any:
    """Build a safe summary of parsed XML (keys, list lengths) for debugging empty responses."""
    if depth >= max_depth:
        return "..."
    if isinstance(obj, dict):
        return {k: _structure_summary(v, max_depth, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return f"<list len={len(obj)}>" if len(obj) > 5 else [_structure_summary(item, max_depth, depth + 1) for item in obj[:5]]
    return type(obj).__name__


def _looks_like_device(d: Any) -> bool:
    """True if d is a dict with at least one device-identifying key (deviceId, name, etc.)."""
    if not isinstance(d, dict):
        return False
    device_keys = ("deviceid", "devicename", "name", "externalid", "imei", "description")
    for k in d.keys():
        if isinstance(k, str) and k.split(":")[-1].lower() in device_keys:
            return True
    return False


def _find_device_list_in_doc(doc: Any) -> List[Dict[str, Any]]:
    """
    Recursively search parsed SOAP doc for a list of dicts that look like device records.
    Used as last resort when response structure differs from WSDL.
    """
    if isinstance(doc, list):
        # At least one item must look like a device; return all dict items that do
        device_like = [item for item in doc if isinstance(item, dict) and _looks_like_device(item)]
        if device_like:
            return device_like
        return []
    if isinstance(doc, dict):
        for v in doc.values():
            out = _find_device_list_in_doc(v)
            if out:
                return out
    return []


def _extract_list(doc: Dict[str, Any], path: List[str]) -> List[Dict[str, Any]]:
    """
    Traverse xmltodict map with case-tolerant Envelope/Body and return a list.
    Handles namespaced elements (e.g., a:Device).
    When the API returns multiple sibling elements (e.g. deviceList = [Device, Device]),
    xmltodict gives a list at the container; treat that as the final list of items.
    """
    cur: Any = doc
    for key in path:
        if isinstance(cur, list):
            return cur  # Already a list of items (e.g. deviceList = [Device, Device, ...])
        if not isinstance(cur, dict):
            return []
        if key in ("Envelope", "Body"):
            k = _first_key_like(cur, key)
            cur = cur.get(k, {})
        else:
            # Try exact match first
            if key in cur:
                cur = cur.get(key, {})
            else:
                # Try with namespace prefix (e.g., a:Device for Device); match case-insensitively
                found = False
                key_lower = key.lower()
                for dict_key in cur.keys():
                    if isinstance(dict_key, str) and dict_key.split(":")[-1].lower() == key_lower:
                        cur = cur[dict_key]
                        found = True
                        break
                if not found:
                    cur = cur.get(key, {})
    
    if isinstance(cur, list):
        return cur
    if isinstance(cur, dict) and cur:
        return [cur]
    return []


def _first_key_like(d: Dict[str, Any], short: str) -> str:
    short_lower = short.lower()
    for k in d.keys():
        if isinstance(k, str) and k.split(":")[-1].lower() == short_lower:
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


def _get_field(d: Dict[str, Any], *field_names: str) -> Any:
    """
    Get field from dict, trying multiple name variations and namespace prefixes.
    Example: _get_field(pos, "deviceId", "DeviceId", "deviceID")
    Also handles namespace prefixes like "a:deviceId", "ns:DeviceId", etc.
    """
    for field_name in field_names:
        # Try exact match first
        if field_name in d:
            return d[field_name]
        
        # Try with namespace prefixes
        for key in d.keys():
            if isinstance(key, str) and key.split(":")[-1] == field_name:
                return d[key]
    
    return None


def _to_string(v: Any) -> Optional[str]:
    """
    Convert value to string, handling dict/object responses from xmltodict.
    XML elements might be parsed as dicts with #text or $ keys, or as complex DateTime structures.
    """
    if v is None or v == "":
        return None
    if isinstance(v, dict):
        # Check for DateTime structure (Remora API specific)
        # Format: {'a:year': '2025', 'a:month': '9', 'a:day': '30', 'a:hour': '5', 'a:minute': '51', 'a:seconds': '17', 'a:timezone': 'UTC'}
        if any(k.endswith(':year') or k.endswith(':month') or k.endswith(':day') for k in v.keys()):
            # Extract date/time components, handling namespace prefixes
            year = _get_field(v, "year")
            month = _get_field(v, "month")
            day = _get_field(v, "day")
            hour = _get_field(v, "hour")
            minute = _get_field(v, "minute")
            seconds = _get_field(v, "seconds") or _get_field(v, "second")
            
            if year and month and day:
                # Format as ISO 8601 datetime string
                hour = hour or "0"
                minute = minute or "0"
                seconds = seconds or "0"
                return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}T{str(hour).zfill(2)}:{str(minute).zfill(2)}:{str(seconds).zfill(2)}Z"
        
        # xmltodict often uses #text for element text content, or $ for attributes
        text = v.get("#text") or v.get("$") or v.get("_text")
        if text:
            return str(text)
        
        # Last resort: convert dict to string
        return str(v)
    
    return str(v)


def _pos_to_row(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Per WSDL: Position has deviceId, coordinate{latitude,longitude}, dateTime, lastCommunicationDateTime, heading, speed, ignitionState, mileage.
    # See: GetPositionsResponse/positionList/Position schema. 
    dev = _get_field(p, "deviceId", "DeviceId", "deviceID")
    coord = _get_field(p, "coordinate", "Coordinate") or {}
    lat = _to_float(_get_field(coord, "latitude", "lat"))
    lon = _to_float(_get_field(coord, "longitude", "lon"))
    if dev and lat is not None and lon is not None:
        # Get ignition state and convert to string
        ignition_raw = _get_field(p, "ignitionState", "IgnitionState")
        ignition_str = _to_string(ignition_raw)
        ignition = ignition_str.upper() if ignition_str else None
        
        # Get timestamp and convert to string
        timestamp_raw = _get_field(p, "dateTime", "DateTime", "lastCommunicationDateTime")
        timestamp = _to_string(timestamp_raw)
        
        # Extract fuel level from position data if available
        fuel_l = _to_float(_get_field(p, "fuel", "Fuel", "fuelLevel", "FuelLevel", "fuelLevelPercent", "FuelLevelPercent", "fuelPercentage", "FuelPercentage", "fuelPercent", "FuelPercent"))
        _LOG.info(f"Remora fuel level debug - raw position data: {p}")
        _LOG.info(f"Remora fuel level debug - extracted fuel_l: {fuel_l}, type: {type(fuel_l)}")
        
        return {
            "device_id": str(dev),
            "latitude": lat,
            "longitude": lon,
            "speed_kph": _to_float(_get_field(p, "speed", "Speed")),
            "heading_deg": _to_float(_get_field(p, "heading", "Heading")),
            "ignition": ignition,
            "timestamp": timestamp,
            "fuel_l": fuel_l,  # Add fuel level to position data
            "raw": p,
        }
    return None


def _harsh_to_row(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coord = _get_field(ev, "coordinate", "Coordinate") or {}
    return {
        "device_id": str(_get_field(ev, "deviceId", "DeviceId") or ""),
        "latitude": _to_float(_get_field(coord, "latitude", "lat")),
        "longitude": _to_float(_get_field(coord, "longitude", "lon")),
        "event_type": _to_string(_get_field(ev, "eventType", "EventType")),
        "speed_kph": _to_float(_get_field(ev, "speed", "Speed")),
        "timestamp": _to_string(_get_field(ev, "dateTime", "DateTime")),
        "raw": ev,
    }


def _geo_to_row(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return {
        "device_id": str(_get_field(ev, "deviceId", "DeviceId") or ""),
        "geofence_name": _to_string(_get_field(ev, "geoFenceName", "GeoFenceName")),
        "start": _to_string(_get_field(ev, "startDateTime", "StartDateTime")),
        "end": _to_string(_get_field(ev, "enddateTime", "EndDateTime")),
        "raw": ev,
    }


def _extract_temperature_from_position(pos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract temperature data from position data if available"""
    device_id = _get_field(pos, "deviceId", "DeviceId")
    if not device_id:
        return None
    
    # Look for temperature fields in the position data
    temp_c = _to_float(_get_field(pos, "temperature", "Temperature", "temp", "Temp", "ambientTemperature", "AmbientTemperature"))
    
    if temp_c is None:
        return None
    
    return {
        "external_id": str(device_id),
        "ts": _to_string(_get_field(pos, "dateTime", "DateTime")),
        "sensor": "ambient",
        "temperature_c": temp_c,
        "raw": pos,
    }


def _can_to_row(can_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert CAN data to normalized row format with fuel level"""
    dev = _get_field(can_data, "deviceId", "DeviceId")
    if not dev:
        return None
    
    # Get coordinates from CAN data
    coord = _get_field(can_data, "coordinate", "Coordinate")
    lat = None
    lon = None
    if coord:
        lat = _to_float(_get_field(coord, "latitude", "Latitude"))
        lon = _to_float(_get_field(coord, "longitude", "Longitude"))
    
    # Get timestamp
    timestamp_raw = _get_field(can_data, "dateTime", "DateTime")
    timestamp = _to_string(timestamp_raw)
    
    # Extract fuel level from CAN data - this is the correct source!
    fuel_l = _to_float(_get_field(can_data, "fuelLevel", "FuelLevel"))
    fuel_l_percent = _to_float(_get_field(can_data, "fuelLevelPercent", "FuelLevelPercent"))
    
    _LOG.info(f"Remora CAN fuel level debug - raw CAN data: {can_data}")
    _LOG.info(f"Remora CAN fuel level debug - fuelLevel: {fuel_l}, fuelLevelPercent: {fuel_l_percent}")
    
    # Use fuelLevelPercent if available, otherwise use fuelLevel
    final_fuel_l = fuel_l_percent if fuel_l_percent is not None else fuel_l
    
    return {
        "device_id": str(dev),
        "latitude": lat,
        "longitude": lon,
        "speed_kph": _to_float(_get_field(can_data, "speed", "Speed")),
        "timestamp": timestamp,
        "fuel_l": final_fuel_l,  # Fuel level from CAN data
        "rpm": _to_float(_get_field(can_data, "rpm", "RPM")),
        "engine_hours": _to_float(_get_field(can_data, "totalEngineHours", "TotalEngineHours")),
        "coolant_c": _to_float(_get_field(can_data, "coolantTemp", "CoolantTemp")),
        "ambient_c": _to_float(_get_field(can_data, "ambientTemp", "AmbientTemp")),
        "raw": can_data,
    }
