"""
IATA Cargo-XML Base Connector
Base class for all IATA integrations providing common functionality
"""

import frappe
import requests
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
from datetime import datetime


class IATAConnector:
    """Base class for IATA API integrations"""
    
    def __init__(self):
        self.settings = frappe.get_single('IATA Settings')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/xml',
            'Accept': 'application/xml'
        })
    
    def authenticate(self) -> bool:
        """Handle IATA API authentication"""
        try:
            if not self.settings.cargo_xml_enabled:
                frappe.throw("IATA Cargo-XML is not enabled")
            
            # Configure authentication headers
            if self.settings.cargo_xml_username and self.settings.cargo_xml_password:
                self.session.auth = (self.settings.cargo_xml_username, self.settings.cargo_xml_password)
            
            return True
        except Exception as e:
            frappe.log_error(f"IATA Authentication Error: {str(e)}")
            return False
    
    def validate_message(self, message: str, schema_type: str = "FWB") -> Dict[str, Any]:
        """Validate XML message against IATA schema"""
        try:
            # Parse XML
            root = ET.fromstring(message)
            
            # Basic XML validation
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Add schema-specific validation logic here
            if schema_type == "FWB":
                validation_result = self._validate_fwb_message(root)
            elif schema_type == "FSU":
                validation_result = self._validate_fsu_message(root)
            elif schema_type == "FMA":
                validation_result = self._validate_fma_message(root)
            
            return validation_result
            
        except ET.ParseError as e:
            return {
                "valid": False,
                "errors": [f"XML Parse Error: {str(e)}"],
                "warnings": []
            }
        except Exception as e:
            frappe.log_error(f"Message validation error: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Validation Error: {str(e)}"],
                "warnings": []
            }
    
    def send_message(self, message_type: str, content: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Send message to IATA platform"""
        try:
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Use default endpoint if not provided
            if not endpoint:
                endpoint = self.settings.cargo_xml_endpoint
            
            if not endpoint:
                raise Exception("No endpoint configured")
            
            # Validate message before sending
            validation = self.validate_message(content, message_type)
            if not validation["valid"]:
                raise Exception(f"Message validation failed: {validation['errors']}")
            
            # Send message
            response = self.session.post(
                endpoint,
                data=content,
                timeout=30
            )
            
            # Log transaction
            self.log_transaction({
                "message_type": message_type,
                "direction": "outbound",
                "status": "sent" if response.status_code == 200 else "failed",
                "response_code": response.status_code,
                "response_content": response.text[:1000],  # Limit log size
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response": response.text,
                "validation": validation
            }
            
        except Exception as e:
            frappe.log_error(f"Send message error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "validation": {"valid": False, "errors": [str(e)], "warnings": []}
            }
    
    def receive_message(self, message_type: str, content: str) -> Dict[str, Any]:
        """Receive and process incoming messages"""
        try:
            # Parse incoming XML
            root = ET.fromstring(content)
            
            # Extract message data
            message_data = self._extract_message_data(root, message_type)
            
            # Log transaction
            self.log_transaction({
                "message_type": message_type,
                "direction": "inbound",
                "status": "received",
                "message_data": message_data,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "data": message_data
            }
            
        except Exception as e:
            frappe.log_error(f"Receive message error: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def log_transaction(self, transaction_data: Dict[str, Any]) -> None:
        """Log all API transactions for audit"""
        try:
            # Create IATA Message Queue record
            message_queue = frappe.get_doc({
                "doctype": "IATA Message Queue",
                "message_type": transaction_data.get("message_type"),
                "direction": transaction_data.get("direction"),
                "status": transaction_data.get("status"),
                "message_content": transaction_data.get("response_content", ""),
                "reference_doctype": transaction_data.get("reference_doctype"),
                "reference_name": transaction_data.get("reference_name"),
                "error_log": json.dumps(transaction_data.get("errors", [])),
                "retry_count": 0
            })
            message_queue.insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Transaction logging error: {str(e)}")
    
    def _validate_fwb_message(self, root: ET.Element) -> Dict[str, Any]:
        """Validate FWB (Freight Waybill) message"""
        errors = []
        warnings = []
        
        # Check required elements for FWB
        required_elements = [
            "MessageHeader",
            "AirWaybill",
            "Origin",
            "Destination",
            "Shipper",
            "Consignee"
        ]
        
        for element in required_elements:
            if root.find(element) is None:
                errors.append(f"Missing required element: {element}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_fsu_message(self, root: ET.Element) -> Dict[str, Any]:
        """Validate FSU (Freight Status Update) message"""
        errors = []
        warnings = []
        
        # Check required elements for FSU
        required_elements = [
            "MessageHeader",
            "AirWaybill",
            "StatusUpdate"
        ]
        
        for element in required_elements:
            if root.find(element) is None:
                errors.append(f"Missing required element: {element}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _validate_fma_message(self, root: ET.Element) -> Dict[str, Any]:
        """Validate FMA (Freight Movement Advice) message"""
        errors = []
        warnings = []
        
        # Check required elements for FMA
        required_elements = [
            "MessageHeader",
            "FlightInfo",
            "CargoManifest"
        ]
        
        for element in required_elements:
            if root.find(element) is None:
                errors.append(f"Missing required element: {element}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def _extract_message_data(self, root: ET.Element, message_type: str) -> Dict[str, Any]:
        """Extract structured data from XML message"""
        data = {}
        
        try:
            # Extract common elements
            if root.find("MessageHeader") is not None:
                header = root.find("MessageHeader")
                data["message_id"] = header.get("MessageId")
                data["sender_id"] = header.get("SenderId")
                data["recipient_id"] = header.get("RecipientId")
                data["timestamp"] = header.get("Timestamp")
            
            # Extract message-specific data
            if message_type == "FWB":
                data.update(self._extract_fwb_data(root))
            elif message_type == "FSU":
                data.update(self._extract_fsu_data(root))
            elif message_type == "FMA":
                data.update(self._extract_fma_data(root))
            
        except Exception as e:
            frappe.log_error(f"Data extraction error: {str(e)}")
        
        return data
    
    def _extract_fwb_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract FWB-specific data"""
        data = {}
        
        if root.find("AirWaybill") is not None:
            awb = root.find("AirWaybill")
            data["awb_number"] = awb.get("AWBNo")
            data["awb_type"] = awb.get("AWBType")
        
        if root.find("Origin") is not None:
            origin = root.find("Origin")
            data["origin_airport"] = origin.get("AirportCode")
        
        if root.find("Destination") is not None:
            dest = root.find("Destination")
            data["destination_airport"] = dest.get("AirportCode")
        
        return data
    
    def _extract_fsu_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract FSU-specific data"""
        data = {}
        
        if root.find("AirWaybill") is not None:
            awb = root.find("AirWaybill")
            data["awb_number"] = awb.get("AWBNo")
        
        if root.find("StatusUpdate") is not None:
            status = root.find("StatusUpdate")
            data["status_code"] = status.get("StatusCode")
            data["status_description"] = status.get("StatusDescription")
            data["timestamp"] = status.get("Timestamp")
        
        return data
    
    def _extract_fma_data(self, root: ET.Element) -> Dict[str, Any]:
        """Extract FMA-specific data"""
        data = {}
        
        if root.find("FlightInfo") is not None:
            flight = root.find("FlightInfo")
            data["flight_number"] = flight.get("FlightNo")
            data["flight_date"] = flight.get("FlightDate")
        
        return data
