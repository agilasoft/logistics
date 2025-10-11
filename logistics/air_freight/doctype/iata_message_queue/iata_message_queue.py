import frappe
from frappe.model.document import Document


class IATAMessageQueue(Document):
    """IATA Message Queue for tracking XML messages"""
    
    def before_insert(self):
        """Set created timestamp"""
        if not self.created_timestamp:
            self.created_timestamp = frappe.utils.now()
    
    def process_message(self):
        """Process the message based on type and direction"""
        try:
            if self.direction == "Outbound":
                self._process_outbound_message()
            elif self.direction == "Inbound":
                self._process_inbound_message()
            
            self.status = "Processed"
            self.processed_timestamp = frappe.utils.now()
            self.save()
            
        except Exception as e:
            frappe.log_error(f"Message processing error: {str(e)}")
            self.status = "Failed"
            self.error_log = str(e)
            self.save()
    
    def _process_outbound_message(self):
        """Process outbound message"""
        from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
        
        message_builder = MessageBuilder()
        
        if self.message_type == "FWB":
            message_builder.send_fwb_message(self.reference_name)
        elif self.message_type == "FSU":
            message_builder.send_fsu_message(self.reference_name)
        elif self.message_type == "FMA":
            message_builder.send_fma_message(self.reference_name)
    
    def _process_inbound_message(self):
        """Process inbound message"""
        from logistics.air_freight.iata_cargo_xml.message_parser import MessageParser
        
        message_parser = MessageParser()
        message_parser.process_incoming_message(self.message_content, self.message_type)
