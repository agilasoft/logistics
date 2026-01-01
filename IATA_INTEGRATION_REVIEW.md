# IATA Integration Implementation Review

## Overview
The IATA (International Air Transport Association) integration in the air_freight module provides Cargo-XML message handling for air freight shipments. It supports sending and receiving standardized IATA messages for freight waybills, status updates, and movement advice.

## Architecture

### Core Components

1. **Base Connector** (`iata_cargo_xml/base_connector.py`)
   - Base class `IATAConnector` providing common functionality
   - Authentication handling
   - Message validation
   - Message sending/receiving
   - Transaction logging

2. **Message Builder** (`iata_cargo_xml/message_builder.py`)
   - Builds XML messages for outbound communication
   - Supports three message types:
     - **FWB** (Freight Waybill): Complete shipment information
     - **FSU** (Freight Status Update): Status updates (departed, arrived, delivered, etc.)
     - **FMA** (Freight Movement Advice): Flight and cargo manifest information

3. **Message Parser** (`iata_cargo_xml/message_parser.py`)
   - Parses incoming XML messages
   - Updates Air Shipment records based on received data
   - Creates milestones for status updates
   - Handles FWB, FSU, and FMA message types

4. **API Endpoints** (`api/iata_cargo_xml_api.py`)
   - REST API for sending/receiving messages
   - Webhook endpoint for incoming messages
   - Message queue management
   - Connection testing

5. **Message Queue** (`doctype/iata_message_queue/`)
   - Tracks all IATA messages (inbound and outbound)
   - Stores message content, status, and processing information
   - Supports retry mechanism for failed messages

6. **Settings** (`doctype/iata_settings/`)
   - Centralized configuration for IATA integrations
   - Supports multiple IATA services:
     - Cargo-XML
     - DG AutoCheck (Dangerous Goods)
     - CASSLink (Cargo Accounts Settlement Systems)
     - TACT (The Air Cargo Tariff)
     - Track & Trace
     - EPIC Partner Verification

## Message Types

### FWB (Freight Waybill Message)
- **Purpose**: Send complete shipment information
- **Contains**: 
  - Air waybill information
  - Origin and destination
  - Shipper and consignee details
  - Cargo details (weight, volume, packages)
  - Routing information
  - Handling information (including dangerous goods)

### FSU (Freight Status Update)
- **Purpose**: Send status updates for shipments
- **Contains**:
  - Air waybill reference
  - Status code (ACC, DEP, ARR, DLV, RCF, CCO)
  - Status description
  - Timestamp
  - Location information

### FMA (Freight Movement Advice)
- **Purpose**: Send flight and cargo manifest information
- **Contains**:
  - Flight information (number, date, aircraft type)
  - Cargo manifest with linked shipments
  - Master AWB number

## Integration Points

### Air Shipment Integration
- Air Shipment doctype has IATA-related fields:
  - `iata_section`: Section for IATA integration
  - `iata_status`: Current IATA status
  - `iata_message_id`: Reference to IATA message
- Methods available:
  - `lookup_tact_rate()`: Lookup TACT rates (placeholder implementation)
  - `create_eawb()`: Create e-AWB (placeholder implementation)

### Location Integration
- Locations can have `custom_iata_code` field
- IATA codes are used for airport identification in messages

## Configuration

### IATA Settings
Access via: **Air Freight > IATA Settings**

Required settings for Cargo-XML:
- Enable Cargo-XML
- Cargo-XML Endpoint URL
- Username
- Password

Optional settings:
- Test Mode: Use test endpoint
- Debug Logging: Enable detailed logging
- Test Endpoint URL: For testing purposes

## How to Test the IATA Integration

### 1. Configuration Setup

```python
# Via Frappe Console or API
import frappe

# Get or create IATA Settings
settings = frappe.get_single("IATA Settings")
settings.cargo_xml_enabled = 1
settings.cargo_xml_endpoint = "https://test-iata-endpoint.com/api/cargo-xml"
settings.cargo_xml_username = "test_username"
settings.cargo_xml_password = "test_password"
settings.test_mode = 1  # Enable test mode
settings.debug_logging = 1  # Enable debug logging
settings.save()
```

### 2. Test Connection

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.test_iata_connection" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET"
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector

connector = IATAConnector()
result = connector.authenticate()
print(f"Authentication: {result}")
```

### 3. Test Message Building (FWB)

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fwb_message" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"air_freight_job_name": "AIR-00001"}'
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder

builder = MessageBuilder()

# Build FWB message (without sending)
xml_content = builder.build_fwb_message("AIR-00001")
print(xml_content)

# Send FWB message
result = builder.send_fwb_message("AIR-00001")
print(result)
```

### 4. Test Message Building (FSU)

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fsu_message" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "air_freight_job_name": "AIR-00001",
    "status_code": "DEP",
    "status_description": "Departed"
  }'
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder

builder = MessageBuilder()
result = builder.send_fsu_message("AIR-00001", "DEP", "Departed")
print(result)
```

### 5. Test Message Building (FMA)

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fma_message" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"master_awb_name": "MAWB-00001"}'
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder

builder = MessageBuilder()
result = builder.send_fma_message("MAWB-00001")
print(result)
```

### 6. Test Message Validation

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.validate_xml_message" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "xml_content": "<FWB>...</FWB>",
    "message_type": "FWB"
  }'
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector

connector = IATAConnector()
xml_content = "<FWB xmlns='http://www.iata.org/IATA/CargoXML/1.0'>...</FWB>"
result = connector.validate_message(xml_content, "FWB")
print(result)
```

### 7. Test Incoming Messages (Webhook)

**Simulate incoming FSU message:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.receive_cargo_xml" \
  -H "Content-Type: application/xml" \
  -H "X-Sender-ID: IATA_PLATFORM" \
  -H "X-Message-ID: MSG-12345" \
  -d '<?xml version="1.0"?>
<FSU xmlns="http://www.iata.org/IATA/CargoXML/1.0">
  <MessageHeader MessageId="FSU_12345" SenderId="IATA_PLATFORM" 
                 RecipientId="logistics.agilasoft.com" 
                 Timestamp="2025-01-15T10:00:00" MessageType="FSU"/>
  <AirWaybillReference AWBNo="AIR-00001"/>
  <StatusUpdate StatusCode="DEP" StatusDescription="Departed" 
                Timestamp="2025-01-15T10:00:00">
    <Location AirportCode="LAX"/>
  </StatusUpdate>
</FSU>'
```

**Via Frappe Console:**
```python
from logistics.air_freight.iata_cargo_xml.message_parser import MessageParser

parser = MessageParser()
xml_content = """<?xml version="1.0"?>
<FSU xmlns="http://www.iata.org/IATA/CargoXML/1.0">
  <MessageHeader MessageId="FSU_12345" SenderId="IATA_PLATFORM" 
                 RecipientId="logistics.agilasoft.com" 
                 Timestamp="2025-01-15T10:00:00" MessageType="FSU"/>
  <AirWaybillReference AWBNo="AIR-00001"/>
  <StatusUpdate StatusCode="DEP" StatusDescription="Departed" 
                Timestamp="2025-01-15T10:00:00">
    <Location AirportCode="LAX"/>
  </StatusUpdate>
</FSU>"""

result = parser.process_incoming_message(xml_content, "FSU")
print(result)
```

### 8. Check Message Queue

**Via API:**
```bash
curl -X GET "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.get_message_queue" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET"
```

**Via Frappe Console:**
```python
import frappe

messages = frappe.get_all("IATA Message Queue",
                         fields=["name", "message_type", "direction", "status", 
                                "reference_name", "created_timestamp"],
                         order_by="created_timestamp desc",
                         limit=10)
for msg in messages:
    print(f"{msg.message_type} - {msg.direction} - {msg.status} - {msg.reference_name}")
```

### 9. Retry Failed Messages

**Via API:**
```bash
curl -X POST "http://your-site/api/method/logistics.air_freight.api.iata_cargo_xml_api.retry_failed_message" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"message_queue_name": "IATA-MSG-00001"}'
```

**Via Frappe Console:**
```python
import frappe

message_queue = frappe.get_doc("IATA Message Queue", "IATA-MSG-00001")
message_queue.process_message()
```

## Testing Checklist

### Prerequisites
- [ ] IATA Settings configured with test credentials
- [ ] Test mode enabled
- [ ] At least one Air Shipment record exists
- [ ] Locations have IATA codes configured (if needed)

### Functional Tests
- [ ] Test connection authentication
- [ ] Build FWB message for an Air Shipment
- [ ] Build FSU message with different status codes
- [ ] Build FMA message for a Master AWB
- [ ] Validate XML message structure
- [ ] Send FWB message (if test endpoint available)
- [ ] Process incoming FSU message
- [ ] Check message queue for sent/received messages
- [ ] Retry failed message

### Integration Tests
- [ ] Verify Air Shipment status updates from FSU messages
- [ ] Verify milestone creation from status updates
- [ ] Verify message queue tracking
- [ ] Verify error handling and logging

### Edge Cases
- [ ] Missing required fields in Air Shipment
- [ ] Invalid IATA codes
- [ ] Network timeout scenarios
- [ ] Invalid XML format
- [ ] Missing authentication credentials

## Monitoring and Debugging

### Message Queue
- View all messages: **Air Freight > IATA Message Queue**
- Filter by status, message type, or direction
- Check error logs for failed messages

### Error Logs
- Check Frappe Error Log: **Setup > Error Log**
- Filter by "IATA" to see IATA-related errors

### Debug Logging
- Enable debug logging in IATA Settings
- Check console output or log files for detailed information

## Known Limitations

1. **TACT Rate Lookup**: Currently a placeholder - requires actual TACT API integration
2. **e-AWB Creation**: Currently a placeholder - requires actual e-AWB API integration
3. **Schema Validation**: Basic validation only - full XSD schema validation not implemented
4. **Retry Mechanism**: Manual retry only - no automatic retry scheduler
5. **Message Queue Processing**: No scheduled job to automatically process pending messages

## Recommendations for Production

1. **Add Scheduled Job**: Create a scheduled job to automatically process pending messages in the queue
2. **Implement Retry Logic**: Add automatic retry with exponential backoff
3. **Add Webhook Security**: Implement webhook signature verification for incoming messages
4. **Complete TACT Integration**: Implement actual TACT API calls for rate lookups
5. **Complete e-AWB Integration**: Implement actual e-AWB API calls
6. **Add XSD Validation**: Implement full XML schema validation using IATA XSD files
7. **Add Monitoring**: Set up alerts for failed messages or connection issues
8. **Add Unit Tests**: Create comprehensive unit tests for all message types

## File Structure

```
logistics/air_freight/
├── iata_cargo_xml/
│   ├── base_connector.py      # Base connector class
│   ├── message_builder.py     # Outbound message building
│   └── message_parser.py       # Inbound message parsing
├── api/
│   └── iata_cargo_xml_api.py  # REST API endpoints
└── doctype/
    ├── iata_settings/          # IATA configuration
    └── iata_message_queue/     # Message tracking
```

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.test_iata_connection` | POST | Test connection |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fwb_message` | POST | Send FWB message |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fsu_message` | POST | Send FSU message |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.send_fma_message` | POST | Send FMA message |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.receive_cargo_xml` | POST | Receive incoming message (webhook) |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.validate_xml_message` | POST | Validate XML message |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.get_message_queue` | GET | Get message queue |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.retry_failed_message` | POST | Retry failed message |
| `/api/method/logistics.air_freight.api.iata_cargo_xml_api.get_iata_settings` | GET | Get IATA settings |

