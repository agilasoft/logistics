"""
IATA Cargo-XML API Endpoints
REST API endpoints for handling IATA Cargo-XML messages
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
import json


@frappe.whitelist(allow_guest=True)
def receive_cargo_xml():
    """Receive incoming IATA Cargo-XML messages via webhook"""
    try:
        # Get XML content from request
        xml_content = frappe.request.get_data(as_text=True)
        
        if not xml_content:
            return {"success": False, "error": "No XML content received"}
        
        # Determine message type from XML
        message_type = _determine_message_type(xml_content)
        
        if not message_type:
            return {"success": False, "error": "Unable to determine message type"}
        
        # Process the message
        from logistics.air_freight.iata_cargo_xml.message_parser import MessageParser
        
        parser = MessageParser()
        result = parser.process_incoming_message(xml_content, message_type)
        
        # Log the webhook call
        frappe.get_doc({
            "doctype": "IATA Message Queue",
            "message_type": message_type,
            "direction": "Inbound",
            "status": "Received",
            "message_content": xml_content,
            "created_timestamp": now_datetime(),
            "sender_id": frappe.request.headers.get("X-Sender-ID", "Unknown"),
            "message_id": frappe.request.headers.get("X-Message-ID", "Unknown")
        }).insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message_type": message_type,
            "result": result
        }
        
    except Exception as e:
        frappe.log_error(f"IATA webhook error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_fwb_message(air_freight_job_name):
    """Send FWB (Freight Waybill) message for an air freight job"""
    try:
        from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
        
        builder = MessageBuilder()
        result = builder.send_fwb_message(air_freight_job_name)
        
        return {
            "success": result["success"],
            "message": "FWB message sent successfully" if result["success"] else f"Failed to send FWB: {result.get('error', 'Unknown error')}",
            "validation": result.get("validation", {})
        }
        
    except Exception as e:
        frappe.log_error(f"Send FWB API error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_fsu_message(air_freight_job_name, status_code="DEP", status_description="Departed"):
    """Send FSU (Freight Status Update) message for an air freight job"""
    try:
        from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
        
        builder = MessageBuilder()
        result = builder.send_fsu_message(air_freight_job_name, status_code, status_description)
        
        return {
            "success": result["success"],
            "message": "FSU message sent successfully" if result["success"] else f"Failed to send FSU: {result.get('error', 'Unknown error')}",
            "validation": result.get("validation", {})
        }
        
    except Exception as e:
        frappe.log_error(f"Send FSU API error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def send_fma_message(master_awb_name):
    """Send FMA (Freight Movement Advice) message for a master air waybill"""
    try:
        from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
        
        builder = MessageBuilder()
        result = builder.send_fma_message(master_awb_name)
        
        return {
            "success": result["success"],
            "message": "FMA message sent successfully" if result["success"] else f"Failed to send FMA: {result.get('error', 'Unknown error')}",
            "validation": result.get("validation", {})
        }
        
    except Exception as e:
        frappe.log_error(f"Send FMA API error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_message_queue(status=None, message_type=None, direction=None):
    """Get IATA message queue entries with optional filters"""
    try:
        filters = {}
        
        if status:
            filters["status"] = status
        if message_type:
            filters["message_type"] = message_type
        if direction:
            filters["direction"] = direction
        
        messages = frappe.get_all("IATA Message Queue",
                                filters=filters,
                                fields=["name", "message_type", "direction", "status", 
                                       "reference_doctype", "reference_name", "created_timestamp",
                                       "processed_timestamp", "retry_count", "sender_id", "message_id"],
                                order_by="created_timestamp desc",
                                limit=100)
        
        return {
            "success": True,
            "messages": messages
        }
        
    except Exception as e:
        frappe.log_error(f"Get message queue error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def retry_failed_message(message_queue_name):
    """Retry a failed message from the queue"""
    try:
        message_queue = frappe.get_doc("IATA Message Queue", message_queue_name)
        
        if message_queue.status != "Failed":
            return {"success": False, "error": "Message is not in failed status"}
        
        if message_queue.retry_count >= 3:
            return {"success": False, "error": "Maximum retry count exceeded"}
        
        # Reset status and increment retry count
        message_queue.status = "Pending"
        message_queue.retry_count += 1
        message_queue.save()
        
        # Process the message
        message_queue.process_message()
        
        return {
            "success": True,
            "message": f"Message retry initiated (attempt {message_queue.retry_count})"
        }
        
    except Exception as e:
        frappe.log_error(f"Retry message error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def validate_xml_message(xml_content, message_type="FWB"):
    """Validate XML message against IATA schema"""
    try:
        from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector
        
        connector = IATAConnector()
        validation_result = connector.validate_message(xml_content, message_type)
        
        return {
            "success": True,
            "validation": validation_result
        }
        
    except Exception as e:
        frappe.log_error(f"XML validation error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_iata_settings():
    """Get current IATA settings"""
    try:
        settings = frappe.get_single("IATA Settings")
        
        # Don't expose sensitive information
        return {
            "success": True,
            "settings": {
                "cargo_xml_enabled": settings.cargo_xml_enabled,
                "dg_autocheck_enabled": settings.dg_autocheck_enabled,
                "cass_enabled": settings.cass_enabled,
                "tact_subscription": settings.tact_subscription,
                "net_rates_enabled": settings.net_rates_enabled,
                "track_trace_enabled": settings.track_trace_enabled,
                "epic_enabled": settings.epic_enabled,
                "test_mode": settings.test_mode,
                "debug_logging": settings.debug_logging
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get IATA settings error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_iata_connection():
    """Test IATA API connection"""
    try:
        from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector
        
        connector = IATAConnector()
        auth_result = connector.authenticate()
        
        return {
            "success": auth_result,
            "message": "Connection successful" if auth_result else "Connection failed"
        }
        
    except Exception as e:
        frappe.log_error(f"Test IATA connection error: {str(e)}")
        return {"success": False, "error": str(e)}


def _determine_message_type(xml_content):
    """Determine message type from XML content"""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_content)
        
        # Check root element name
        root_tag = root.tag
        if root_tag.endswith("FWB"):
            return "FWB"
        elif root_tag.endswith("FSU"):
            return "FSU"
        elif root_tag.endswith("FMA"):
            return "FMA"
        elif root_tag.endswith("FHL"):
            return "FHL"
        elif root_tag.endswith("XFWB"):
            return "XFWB"
        elif root_tag.endswith("XFHL"):
            return "XFHL"
        elif root_tag.endswith("XSDG"):
            return "XSDG"
        
        # Check MessageHeader if available
        header = root.find("MessageHeader")
        if header is not None:
            message_type = header.get("MessageType")
            if message_type:
                return message_type
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Determine message type error: {str(e)}")
        return None
