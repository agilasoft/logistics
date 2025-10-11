"""
IATA Cargo-XML Message Builder
Builds XML messages for various IATA message types (FWB, FSU, FMA, etc.)
"""

import frappe
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional
from .base_connector import IATAConnector


class MessageBuilder(IATAConnector):
    """Builds IATA Cargo-XML messages"""
    
    def __init__(self):
        super().__init__()
        self.namespace = "http://www.iata.org/IATA/CargoXML/1.0"
    
    def build_fwb_message(self, air_freight_job_name: str) -> str:
        """Build FWB (Freight Waybill Message) XML"""
        try:
            job = frappe.get_doc("Air Shipment", air_freight_job_name)
            
            # Create root element
            root = ET.Element("FWB")
            root.set("xmlns", self.namespace)
            
            # Add Message Header
            self._add_message_header(root, "FWB", job.name)
            
            # Add Air Waybill Information
            self._add_air_waybill_info(root, job)
            
            # Add Origin and Destination
            self._add_origin_destination(root, job)
            
            # Add Shipper and Consignee
            self._add_shipper_consignee(root, job)
            
            # Add Cargo Details
            self._add_cargo_details(root, job)
            
            # Add Routing Information
            self._add_routing_info(root, job)
            
            # Add Handling Information
            self._add_handling_info(root, job)
            
            # Generate XML string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            
            # Log message creation
            self.log_transaction({
                "message_type": "FWB",
                "direction": "outbound",
                "status": "created",
                "reference_doctype": "Air Shipment",
                "reference_name": job.name,
                "response_content": xml_str[:500]  # Log first 500 chars
            })
            
            return xml_str
            
        except Exception as e:
            frappe.log_error(f"FWB message building error: {str(e)}")
            raise
    
    def build_fsu_message(self, air_freight_job_name: str, status_code: str, status_description: str) -> str:
        """Build FSU (Freight Status Update) XML"""
        try:
            job = frappe.get_doc("Air Shipment", air_freight_job_name)
            
            # Create root element
            root = ET.Element("FSU")
            root.set("xmlns", self.namespace)
            
            # Add Message Header
            self._add_message_header(root, "FSU", job.name)
            
            # Add Air Waybill Reference
            awb_ref = ET.SubElement(root, "AirWaybillReference")
            awb_ref.set("AWBNo", job.master_awb or job.name)
            
            # Add Status Update
            status_update = ET.SubElement(root, "StatusUpdate")
            status_update.set("StatusCode", status_code)
            status_update.set("StatusDescription", status_description)
            status_update.set("Timestamp", datetime.now().isoformat())
            
            # Add Location if available
            if job.origin_port:
                location = ET.SubElement(status_update, "Location")
                location.set("AirportCode", self._get_iata_code(job.origin_port))
            
            # Generate XML string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            
            # Log message creation
            self.log_transaction({
                "message_type": "FSU",
                "direction": "outbound",
                "status": "created",
                "reference_doctype": "Air Shipment",
                "reference_name": job.name,
                "response_content": xml_str[:500]
            })
            
            return xml_str
            
        except Exception as e:
            frappe.log_error(f"FSU message building error: {str(e)}")
            raise
    
    def build_fma_message(self, master_awb_name: str) -> str:
        """Build FMA (Freight Movement Advice) XML"""
        try:
            mawb = frappe.get_doc("Master Air Waybill", master_awb_name)
            
            # Create root element
            root = ET.Element("FMA")
            root.set("xmlns", self.namespace)
            
            # Add Message Header
            self._add_message_header(root, "FMA", mawb.name)
            
            # Add Flight Information
            self._add_flight_info(root, mawb)
            
            # Add Cargo Manifest
            self._add_cargo_manifest(root, mawb)
            
            # Generate XML string
            xml_str = ET.tostring(root, encoding='unicode', method='xml')
            
            # Log message creation
            self.log_transaction({
                "message_type": "FMA",
                "direction": "outbound",
                "status": "created",
                "reference_doctype": "Master Air Waybill",
                "reference_name": mawb.name,
                "response_content": xml_str[:500]
            })
            
            return xml_str
            
        except Exception as e:
            frappe.log_error(f"FMA message building error: {str(e)}")
            raise
    
    def send_fwb_message(self, air_freight_job_name: str) -> Dict[str, Any]:
        """Build and send FWB message"""
        try:
            xml_content = self.build_fwb_message(air_freight_job_name)
            result = self.send_message("FWB", xml_content)
            
            # Queue message for tracking
            self._queue_message("FWB", "outbound", air_freight_job_name, xml_content)
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Send FWB error: {str(e)}")
            raise
    
    def send_fsu_message(self, air_freight_job_name: str, status_code: str = "DEP", status_description: str = "Departed") -> Dict[str, Any]:
        """Build and send FSU message"""
        try:
            xml_content = self.build_fsu_message(air_freight_job_name, status_code, status_description)
            result = self.send_message("FSU", xml_content)
            
            # Queue message for tracking
            self._queue_message("FSU", "outbound", air_freight_job_name, xml_content)
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Send FSU error: {str(e)}")
            raise
    
    def send_fma_message(self, master_awb_name: str) -> Dict[str, Any]:
        """Build and send FMA message"""
        try:
            xml_content = self.build_fma_message(master_awb_name)
            result = self.send_message("FMA", xml_content)
            
            # Queue message for tracking
            self._queue_message("FMA", "outbound", master_awb_name, xml_content)
            
            return result
            
        except Exception as e:
            frappe.log_error(f"Send FMA error: {str(e)}")
            raise
    
    def _add_message_header(self, root: ET.Element, message_type: str, reference: str):
        """Add message header to XML"""
        header = ET.SubElement(root, "MessageHeader")
        header.set("MessageId", f"{message_type}_{reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        header.set("SenderId", frappe.get_site_config().get("site_name", "logistics.agilasoft.com"))
        header.set("RecipientId", "IATA_PLATFORM")
        header.set("Timestamp", datetime.now().isoformat())
        header.set("MessageType", message_type)
    
    def _add_air_waybill_info(self, root: ET.Element, job):
        """Add air waybill information"""
        awb = ET.SubElement(root, "AirWaybill")
        awb.set("AWBNo", job.master_awb or job.name)
        awb.set("AWBType", "H" if job.house_type else "M")
        
        if job.airline:
            airline = frappe.get_doc("Airline", job.airline)
            awb.set("AirlineCode", airline.two_character_code or airline.code)
    
    def _add_origin_destination(self, root: ET.Element, job):
        """Add origin and destination information"""
        # Origin
        origin = ET.SubElement(root, "Origin")
        origin.set("AirportCode", self._get_iata_code(job.origin_port))
        if job.etd:
            origin.set("ETD", job.etd.strftime("%Y-%m-%d"))
        
        # Destination
        destination = ET.SubElement(root, "Destination")
        destination.set("AirportCode", self._get_iata_code(job.destination_port))
        if job.eta:
            destination.set("ETA", job.eta.strftime("%Y-%m-%d"))
    
    def _add_shipper_consignee(self, root: ET.Element, job):
        """Add shipper and consignee information"""
        # Shipper
        shipper = ET.SubElement(root, "Shipper")
        if job.shipper:
            shipper_doc = frappe.get_doc("Shipper", job.shipper)
            shipper.set("Name", shipper_doc.shipper_name or "")
            shipper.set("Address", job.shipper_address_display or "")
        
        # Consignee
        consignee = ET.SubElement(root, "Consignee")
        if job.consignee:
            consignee_doc = frappe.get_doc("Consignee", job.consignee)
            consignee.set("Name", consignee_doc.consignee_name or "")
            consignee.set("Address", job.consignee_address_display or "")
    
    def _add_cargo_details(self, root: ET.Element, job):
        """Add cargo details"""
        cargo = ET.SubElement(root, "Cargo")
        cargo.set("TotalWeight", str(job.weight or 0))
        cargo.set("TotalVolume", str(job.volume or 0))
        cargo.set("ChargeableWeight", str(job.chargeable or job.weight or 0))
        
        # Add package details
        if job.packages:
            for package in job.packages:
                package_elem = ET.SubElement(cargo, "Package")
                package_elem.set("Pieces", str(package.no_of_packs or 1))
                package_elem.set("Weight", str(package.weight or 0))
                package_elem.set("Description", package.goods_description or "")
                
                if package.commodity:
                    package_elem.set("CommodityCode", package.commodity)
    
    def _add_routing_info(self, root: ET.Element, job):
        """Add routing information"""
        routing = ET.SubElement(root, "Routing")
        
        if job.airline:
            airline = frappe.get_doc("Airline", job.airline)
            routing.set("Carrier", airline.two_character_code or airline.code)
        
        if job.master_awb:
            mawb = frappe.get_doc("Master Air Waybill", job.master_awb)
            if mawb.flight_no:
                routing.set("FlightNumber", mawb.flight_no)
    
    def _add_handling_info(self, root: ET.Element, job):
        """Add handling information"""
        handling = ET.SubElement(root, "HandlingInformation")
        
        if job.incoterm:
            handling.set("Incoterm", job.incoterm)
        
        if job.additional_terms:
            handling.set("AdditionalTerms", job.additional_terms)
        
        # Add dangerous goods info if applicable
        if job.packages:
            for package in job.packages:
                if package.dg_substance:
                    dg_info = ET.SubElement(handling, "DangerousGoods")
                    if hasattr(package, 'un_number') and package.un_number:
                        dg_info.set("UNNumber", package.un_number)
                    else:
                        dg_info.set("UNNumber", package.dg_substance)
                    dg_info.set("DGClass", package.dg_class or "")
                    if hasattr(package, 'packing_group') and package.packing_group:
                        dg_info.set("PackingGroup", package.packing_group)
                    if hasattr(package, 'proper_shipping_name') and package.proper_shipping_name:
                        dg_info.set("ProperShippingName", package.proper_shipping_name)
    
    def _add_flight_info(self, root: ET.Element, mawb):
        """Add flight information for FMA"""
        flight_info = ET.SubElement(root, "FlightInfo")
        flight_info.set("FlightNumber", mawb.flight_no or "")
        
        # Use flight_date if available, otherwise fall back to origin_receipt_requested
        flight_date = None
        if hasattr(mawb, 'flight_date') and mawb.flight_date:
            flight_date = mawb.flight_date
        elif mawb.origin_receipt_requested:
            flight_date = mawb.origin_receipt_requested
        
        flight_info.set("FlightDate", flight_date.strftime("%Y-%m-%d") if flight_date else "")
        
        if mawb.aircraft_type:
            flight_info.set("AircraftType", mawb.aircraft_type)
        
        if mawb.aircraft_registration_no:
            flight_info.set("AircraftRegistration", mawb.aircraft_registration_no)
    
    def _add_cargo_manifest(self, root: ET.Element, mawb):
        """Add cargo manifest for FMA"""
        manifest = ET.SubElement(root, "CargoManifest")
        manifest.set("MAWBNumber", mawb.master_awb_no)
        
        # Add linked air freight jobs
        linked_jobs = frappe.get_all("Air Shipment", 
                                   filters={"master_awb": mawb.name},
                                   fields=["name", "weight", "volume"])
        
        for job in linked_jobs:
            job_elem = ET.SubElement(manifest, "Job")
            job_elem.set("JobNumber", job.name)
            job_elem.set("Weight", str(job.weight or 0))
            job_elem.set("Volume", str(job.volume or 0))
    
    def _get_iata_code(self, location_name: str) -> str:
        """Get IATA code for location"""
        try:
            if location_name:
                location = frappe.get_doc("Location", location_name)
                return location.custom_iata_code or location_name[:3].upper()
        except:
            pass
        return location_name[:3].upper() if location_name else "XXX"
    
    def _queue_message(self, message_type: str, direction: str, reference_name: str, content: str):
        """Queue message for processing"""
        try:
            queue_doc = frappe.get_doc({
                "doctype": "IATA Message Queue",
                "message_type": message_type,
                "direction": direction.title(),
                "status": "Pending",
                "reference_doctype": "Air Shipment" if message_type in ["FWB", "FSU"] else "Master Air Waybill",
                "reference_name": reference_name,
                "message_content": content,
                "retry_count": 0
            })
            queue_doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Queue message error: {str(e)}")
