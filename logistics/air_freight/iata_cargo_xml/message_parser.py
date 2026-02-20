"""
IATA Cargo-XML Message Parser
Parses incoming XML messages and updates system records
"""

import frappe
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional
from .base_connector import IATAConnector


class MessageParser(IATAConnector):
    """Parses incoming IATA Cargo-XML messages"""
    
    def __init__(self):
        super().__init__()
        self.namespace = "http://www.iata.org/IATA/CargoXML/1.0"
    
    def process_incoming_message(self, xml_content: str, message_type: str) -> Dict[str, Any]:
        """Process incoming XML message"""
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Extract message data
            message_data = self._extract_message_data(root, message_type)
            
            # Process based on message type
            if message_type == "FSU":
                result = self._process_fsu_message(message_data)
            elif message_type == "FMA":
                result = self._process_fma_message(message_data)
            elif message_type == "FWB":
                result = self._process_fwb_message(message_data)
            else:
                result = {"success": False, "error": f"Unsupported message type: {message_type}"}
            
            # Log processing
            self.log_transaction({
                "message_type": message_type,
                "direction": "inbound",
                "status": "processed" if result["success"] else "failed",
                "message_data": message_data,
                "response_content": str(result)
            })
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Message parsing error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_fsu_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process FSU (Freight Status Update) message"""
        try:
            awb_number = message_data.get("awb_number")
            status_code = message_data.get("status_code")
            status_description = message_data.get("status_description")
            
            if not awb_number:
                return {"success": False, "error": "AWB number not found in FSU message"}
            
            # Find air freight job by AWB number
            job = self._find_job_by_awb(awb_number)
            if not job:
                return {"success": False, "error": f"No job found for AWB: {awb_number}"}
            
            # Update job status based on FSU status
            self._update_job_status(job, status_code, status_description)
            
            # Create milestone entry
            self._create_milestone(job.name, status_code, status_description)
            
            return {
                "success": True,
                "job_updated": job.name,
                "status_code": status_code,
                "status_description": status_description
            }
            
        except Exception as e:
            frappe.log_error(f"FSU processing error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_fma_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process FMA (Freight Movement Advice) message"""
        try:
            flight_number = message_data.get("flight_number")
            flight_date = message_data.get("flight_date")
            
            if not flight_number:
                return {"success": False, "error": "Flight number not found in FMA message"}
            
            # Find master AWB by flight number
            mawb = self._find_mawb_by_flight(flight_number, flight_date)
            if not mawb:
                return {"success": False, "error": f"No MAWB found for flight: {flight_number}"}
            
            # Update flight information
            mawb.flight_no = flight_number
            if flight_date:
                mawb.origin_receipt_requested = datetime.strptime(flight_date, "%Y-%m-%d").date()
            mawb.save()
            
            return {
                "success": True,
                "mawb_updated": mawb.name,
                "flight_number": flight_number,
                "flight_date": flight_date
            }
            
        except Exception as e:
            frappe.log_error(f"FMA processing error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_fwb_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process FWB (Freight Waybill) message - typically for confirmation"""
        try:
            awb_number = message_data.get("awb_number")
            origin_airport = message_data.get("origin_airport")
            destination_airport = message_data.get("destination_airport")
            
            if not awb_number:
                return {"success": False, "error": "AWB number not found in FWB message"}
            
            # Find or create air freight job
            job = self._find_job_by_awb(awb_number)
            if not job:
                # Create new job from FWB data
                job = self._create_job_from_fwb(message_data)
            else:
                # Update existing job
                self._update_job_from_fwb(job, message_data)
            
            return {
                "success": True,
                "job_processed": job.name,
                "action": "created" if not job.get("__islocal") else "updated"
            }
            
        except Exception as e:
            frappe.log_error(f"FWB processing error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _find_job_by_awb(self, awb_number: str) -> Optional[frappe.Document]:
        """Find air freight job by AWB number"""
        try:
            # First try to find by master AWB
            jobs = frappe.get_all("Air Shipment",
                                filters={"master_awb": awb_number},
                                limit=1)
            
            if jobs:
                return frappe.get_doc("Air Shipment", jobs[0].name)
            
            # Then try to find by job name (if AWB matches job name)
            try:
                return frappe.get_doc("Air Shipment", awb_number)
            except Exception:
                pass
            
            # Try to find in master AWB
            mawbs = frappe.get_all("Master Air Waybill",
                                 filters={"master_awb_no": awb_number},
                                 limit=1)
            
            if mawbs:
                # Find jobs linked to this MAWB
                jobs = frappe.get_all("Air Shipment",
                                    filters={"master_awb": mawbs[0].name},
                                    limit=1)
                if jobs:
                    return frappe.get_doc("Air Shipment", jobs[0].name)
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Find job by AWB error: {str(e)}")
            return None
    
    def _find_mawb_by_flight(self, flight_number: str, flight_date: str = None) -> Optional[frappe.Document]:
        """Find master AWB by flight number"""
        try:
            filters = {"flight_no": flight_number}
            if flight_date:
                filters["origin_receipt_requested"] = datetime.strptime(flight_date, "%Y-%m-%d").date()
            
            mawbs = frappe.get_all("Master Air Waybill",
                                 filters=filters,
                                 limit=1)
            
            if mawbs:
                return frappe.get_doc("Master Air Waybill", mawbs[0].name)
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Find MAWB by flight error: {str(e)}")
            return None
    
    def _update_job_status(self, job: frappe.Document, status_code: str, status_description: str):
        """Update job status based on FSU status"""
        try:
            # Map IATA status codes to internal status
            status_mapping = {
                "ACC": "Accepted",  # Cargo accepted
                "DEP": "Departed",  # Departed
                "ARR": "Arrived",   # Arrived
                "DLV": "Delivered", # Delivered
                "RCF": "Ready for Collection", # Ready for collection
                "CCO": "Customs Cleared" # Customs cleared
            }
            
            new_status = status_mapping.get(status_code, status_description)
            
            # Update job with status information
            if not hasattr(job, 'iata_status'):
                frappe.msgprint("IATA Status field not found. Please add the field to Air Shipment doctype.")
                return
            
            job.iata_status = new_status
            job.last_status_update = datetime.now()
            job.save()
            
        except Exception as e:
            frappe.log_error(f"Update job status error: {str(e)}")
    
    def _create_milestone(self, job_name: str, status_code: str, status_description: str):
        """Create milestone entry for status update"""
        try:
            milestone = frappe.get_doc({
                "doctype": "Job Milestone",
                "parent": job_name,
                "parenttype": "Air Shipment",
                "parentfield": "milestones",
                "milestone": status_description,
                "status": "Completed",
                "expected_date": datetime.now().date(),
                "actual_date": datetime.now().date()
            })
            milestone.insert(ignore_permissions=True)
            
        except Exception as e:
            frappe.log_error(f"Create milestone error: {str(e)}")
    
    def _create_job_from_fwb(self, message_data: Dict[str, Any]) -> frappe.Document:
        """Create new air freight job from FWB data"""
        try:
            job = frappe.get_doc({
                "doctype": "Air Shipment",
                "master_awb": message_data.get("awb_number"),
                "direction": "Export",  # Default, should be determined from context
                "origin_port": self._find_location_by_iata(message_data.get("origin_airport")),
                "destination_port": self._find_location_by_iata(message_data.get("destination_airport")),
                "booking_date": datetime.now().date(),
                "iata_status": "Received from IATA",
                "iata_message_id": message_data.get("message_id")
            })
            
            job.insert(ignore_permissions=True)
            return job
            
        except Exception as e:
            frappe.log_error(f"Create job from FWB error: {str(e)}")
            raise
    
    def _update_job_from_fwb(self, job: frappe.Document, message_data: Dict[str, Any]):
        """Update existing job from FWB data"""
        try:
            # Update relevant fields
            if message_data.get("origin_airport"):
                job.origin_port = self._find_location_by_iata(message_data.get("origin_airport"))
            
            if message_data.get("destination_airport"):
                job.destination_port = self._find_location_by_iata(message_data.get("destination_airport"))
            
            job.iata_status = "Confirmed via IATA"
            if message_data.get("message_id"):
                job.iata_message_id = message_data.get("message_id")
            job.save()
            
        except Exception as e:
            frappe.log_error(f"Update job from FWB error: {str(e)}")
    
    def _find_location_by_iata(self, iata_code: str) -> Optional[str]:
        """Find location by IATA code"""
        try:
            if not iata_code:
                return None
            
            locations = frappe.get_all("Location",
                                     filters={"custom_iata_code": iata_code},
                                     limit=1)
            
            if locations:
                return locations[0].name
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Find location by IATA error: {str(e)}")
            return None
