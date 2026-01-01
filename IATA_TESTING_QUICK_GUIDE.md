# IATA Integration - Quick Testing Guide

## Quick Start Testing

### 1. Setup (One-time)

```python
# Via Frappe Console: bench --site [site-name] console
import frappe

settings = frappe.get_single("IATA Settings")
settings.cargo_xml_enabled = 1
settings.cargo_xml_endpoint = "https://test-endpoint.com/api"
settings.cargo_xml_username = "test_user"
settings.cargo_xml_password = "test_pass"
settings.test_mode = 1
settings.save()
```

### 2. Test Connection

```python
from logistics.air_freight.api.iata_cargo_xml_api import test_iata_connection
result = test_iata_connection()
print(result)
```

### 3. Build and View FWB Message

```python
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder

builder = MessageBuilder()
xml = builder.build_fwb_message("AIR-00001")  # Replace with actual Air Shipment name
print(xml)
```

### 4. Send FWB Message

```python
from logistics.air_freight.api.iata_cargo_xml_api import send_fwb_message

result = send_fwb_message("AIR-00001")
print(result)
```

### 5. Check Message Queue

```python
import frappe

messages = frappe.get_all("IATA Message Queue", 
                         fields=["name", "message_type", "status", "created_timestamp"],
                         limit=10)
for m in messages:
    print(f"{m.name}: {m.message_type} - {m.status}")
```

### 6. Test Incoming Message

```python
from logistics.air_freight.iata_cargo_xml.message_parser import MessageParser

xml = """<?xml version="1.0"?>
<FSU xmlns="http://www.iata.org/IATA/CargoXML/1.0">
  <MessageHeader MessageId="TEST" SenderId="IATA" RecipientId="TEST" 
                 Timestamp="2025-01-15T10:00:00" MessageType="FSU"/>
  <AirWaybillReference AWBNo="AIR-00001"/>
  <StatusUpdate StatusCode="DEP" StatusDescription="Departed" 
                Timestamp="2025-01-15T10:00:00"/>
</FSU>"""

parser = MessageParser()
result = parser.process_incoming_message(xml, "FSU")
print(result)
```

## Run Test Suite

```bash
# Via bench command
bench --site [site-name] execute logistics.air_freight.tests.test_iata_integration.test_iata_integration

# Or via Python
bench --site [site-name] console
>>> from logistics.air_freight.tests.test_iata_integration import test_iata_integration
>>> test_iata_integration()
```

## Common Test Scenarios

### Scenario 1: Send Waybill for New Shipment
```python
# 1. Create Air Shipment
job = frappe.get_doc({
    "doctype": "Air Shipment",
    "direction": "Export",
    "origin_port": "Los Angeles",
    "destination_port": "New York",
    "weight": 100,
    "volume": 1
})
job.insert()

# 2. Send FWB
from logistics.air_freight.api.iata_cargo_xml_api import send_fwb_message
result = send_fwb_message(job.name)
print(f"FWB sent: {result['success']}")
```

### Scenario 2: Update Shipment Status
```python
from logistics.air_freight.api.iata_cargo_xml_api import send_fsu_message

# Send status update
result = send_fsu_message("AIR-00001", "DEP", "Departed")
print(result)
```

### Scenario 3: Process Incoming Status Update
```python
from logistics.air_freight.api.iata_cargo_xml_api import receive_cargo_xml

# Simulate webhook call
xml = """<FSU>...</FSU>"""  # Your FSU XML
# Note: This requires webhook endpoint setup
```

## Troubleshooting

### Issue: "IATA Cargo-XML is not enabled"
**Solution:** Enable in IATA Settings
```python
settings = frappe.get_single("IATA Settings")
settings.cargo_xml_enabled = 1
settings.save()
```

### Issue: "No endpoint configured"
**Solution:** Set endpoint in IATA Settings
```python
settings.cargo_xml_endpoint = "https://your-endpoint.com/api"
settings.save()
```

### Issue: Message validation fails
**Solution:** Check XML structure and required fields
```python
from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector
connector = IATAConnector()
result = connector.validate_message(xml_content, "FWB")
print(result["errors"])  # See validation errors
```

### Issue: No job found for AWB
**Solution:** Ensure Air Shipment exists with matching AWB
```python
# Check if job exists
jobs = frappe.get_all("Air Shipment", filters={"name": "AIR-00001"})
print(f"Job exists: {len(jobs) > 0}")
```

## Useful Queries

### View all IATA messages
```python
frappe.get_all("IATA Message Queue", 
               fields=["*"],
               order_by="created_timestamp desc")
```

### View failed messages
```python
frappe.get_all("IATA Message Queue",
               filters={"status": "Failed"},
               fields=["name", "message_type", "error_log"])
```

### View messages for specific shipment
```python
frappe.get_all("IATA Message Queue",
               filters={"reference_name": "AIR-00001"},
               fields=["*"])
```

## API Testing with curl

### Test Connection
```bash
curl -X POST "http://localhost:8000/api/method/logistics.air_freight.api.iata_cargo_xml_api.test_iata_connection" \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET"
```

### Send FWB
```bash
curl -X POST "http://localhost:8000/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fwb_message" \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"air_freight_job_name": "AIR-00001"}'
```

### Get Message Queue
```bash
curl -X GET "http://localhost:8000/api/method/logistics.air_freight.api.iata_cargo_xml_api.get_message_queue" \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET"
```

