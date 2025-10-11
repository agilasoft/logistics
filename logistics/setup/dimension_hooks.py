# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def set_dimensions_in_gl_entry(doc, method):
    """
    Hook function to automatically populate dimensions in GL Entry
    when it's created from documents that have items, job references, or profit centers.
    
    Supports: Sales Invoice, Purchase Invoice, Job documents with charges
    """
    try:
        # Initialize dimensions
        job_reference = None
        item_code = None
        profit_center = None
        
        # Get the reference document that created this GL Entry
        reference_doc = None
        if doc.voucher_type and doc.voucher_no:
            try:
                reference_doc = frappe.get_doc(doc.voucher_type, doc.voucher_no)
            except Exception:
                # If we can't get the reference document, skip
                pass
        
        if reference_doc:
            # Extract dimensions from the source document
            dimensions = extract_dimensions_from_document(reference_doc)
            job_reference = dimensions.get('job_reference')
            item_code = dimensions.get('item_code')
            profit_center = dimensions.get('profit_center')
        
        # Set dimensions in GL Entry if they exist
        if hasattr(doc, 'job_reference') and job_reference:
            doc.job_reference = job_reference
            
        if hasattr(doc, 'item') and item_code:
            doc.item = item_code
            
        if hasattr(doc, 'profit_center') and profit_center:
            doc.profit_center = profit_center
        
    except Exception as e:
        # Log the error but don't break the GL Entry creation
        frappe.logger().error(f"Error setting dimensions in GL Entry: {e}")


def update_gl_entries_dimensions(doc, method):
    """
    Hook function to update dimensions in existing GL entries when source document changes.
    This runs on save/update of source documents.
    """
    try:
        # Only update if document is submitted (has GL entries)
        if doc.docstatus != 1:
            return
            
        # Get existing GL entries for this document
        gl_entries = frappe.get_all('GL Entry',
            filters={
                'voucher_type': doc.doctype,
                'voucher_no': doc.name
            },
            fields=['name', 'item', 'job_reference', 'profit_center']
        )
        
        if not gl_entries:
            return
            
        # Extract dimensions from the updated document
        dimensions = extract_dimensions_from_document(doc)
        item_code = dimensions.get('item_code')
        job_reference = dimensions.get('job_reference')
        profit_center = dimensions.get('profit_center')
        
        # Update GL entries with new dimensions
        for gl_entry in gl_entries:
            update_fields = {}
            
            if item_code and gl_entry.item != item_code:
                update_fields['item'] = item_code
                
            if job_reference and gl_entry.job_reference != job_reference:
                update_fields['job_reference'] = job_reference
                
            if profit_center and gl_entry.profit_center != profit_center:
                update_fields['profit_center'] = profit_center
            
            # Update the GL Entry if there are changes
            if update_fields:
                for field, value in update_fields.items():
                    frappe.db.set_value('GL Entry', gl_entry.name, field, value)
        
        if update_fields:
            frappe.db.commit()
            frappe.msgprint(f"Updated dimensions in {len(gl_entries)} GL entries", alert=True)
        
    except Exception as e:
        frappe.logger().error(f"Error updating GL entries dimensions: {e}")


def validate_dimensions_on_save(doc, method):
    """
    Hook function to validate and update dimensions when document is saved.
    This ensures dimensions are always up-to-date with the transaction data.
    """
    try:
        # Extract dimensions from the document
        dimensions = extract_dimensions_from_document(doc)
        
        # Store dimensions in document for later use
        doc._extracted_dimensions = dimensions
        
        # If document is submitted, update GL entries
        if doc.docstatus == 1:
            update_gl_entries_dimensions(doc, method)
        
    except Exception as e:
        frappe.logger().error(f"Error validating dimensions on save: {e}")


def update_dimensions_on_item_change(doc, method):
    """
    Hook function to populate dimensions in line items when they are added/changed.
    This runs on validate to ensure dimensions are populated before save.
    ERPNext will automatically handle GL Entry posting with the populated dimensions.
    """
    try:
        # Only run for documents that have items
        if not hasattr(doc, 'items') or not doc.items:
            return
            
        # Populate dimension fields in items table
        populate_item_dimensions(doc, {})
        
    except Exception as e:
        frappe.logger().error(f"Error updating dimensions on item change: {e}")


def populate_item_dimensions(doc, dimensions):
    """
    Populate dimension fields in the items table of the document.
    This ensures each line item has the correct item dimension for GL Entry posting.
    """
    try:
        if not hasattr(doc, 'items') or not doc.items:
            return
            
        # Get dimensions from document level
        doc_job_reference = getattr(doc, 'job_reference', None) or getattr(doc, 'job_name', None)
        doc_profit_center = getattr(doc, 'profit_center', None) or getattr(doc, 'cost_center', None)
        
        # Update each item with dimensions
        for item in doc.items:
            # Set item dimension (from item_code) - this is the key for GL Entry posting
            if hasattr(item, 'item') and item.item_code:
                item.item = item.item_code
                
            # Set job reference dimension
            if hasattr(item, 'job_reference') and doc_job_reference:
                item.job_reference = doc_job_reference
                
            # Set profit center dimension
            if hasattr(item, 'profit_center') and doc_profit_center:
                item.profit_center = doc_profit_center
                
    except Exception as e:
        frappe.logger().error(f"Error populating item dimensions: {e}")


def extract_dimensions_from_document(doc):
    """
    Extract dimensions from various document types.
    
    Args:
        doc: The source document (Sales Invoice, Purchase Invoice, Job documents, etc.)
    
    Returns:
        dict: Dictionary with extracted dimensions
    """
    dimensions = {
        'job_reference': None,
        'item_code': None,
        'profit_center': None
    }
    
    try:
        # Extract job_reference
        if hasattr(doc, 'job_reference') and doc.job_reference:
            dimensions['job_reference'] = doc.job_reference
        elif hasattr(doc, 'job_name') and doc.job_name:
            dimensions['job_reference'] = doc.job_name
        
        # Extract item_code from items
        if hasattr(doc, 'items') and doc.items:
            # Get item_code from the first item
            dimensions['item_code'] = doc.items[0].get('item_code')
        elif hasattr(doc, 'charges') and doc.charges:
            # For documents with charges, check if charges have item_code
            for charge in doc.charges:
                if hasattr(charge, 'item_code') and charge.item_code:
                    dimensions['item_code'] = charge.item_code
                    break
        
        # Extract profit_center
        if hasattr(doc, 'profit_center') and doc.profit_center:
            dimensions['profit_center'] = doc.profit_center
        elif hasattr(doc, 'cost_center') and doc.cost_center:
            # Use cost_center as profit_center if profit_center is not set
            dimensions['profit_center'] = doc.cost_center
        
        return dimensions
        
    except Exception as e:
        frappe.logger().error(f"Error extracting dimensions from {doc.doctype}: {e}")
        return dimensions


def get_dimensions_from_document(doc_type: str, doc_name: str):
    """
    Helper function to extract dimensions from various document types.
    This can be used by other modules to get dimensions.
    
    Args:
        doc_type: Type of document
        doc_name: Name of document
    
    Returns:
        dict: Dictionary with dimensions
    """
    try:
        doc = frappe.get_doc(doc_type, doc_name)
        return extract_dimensions_from_document(doc)
        
    except Exception as e:
        frappe.logger().error(f"Error getting dimensions from {doc_type} {doc_name}: {e}")
        return {
            'job_reference': None,
            'item_code': None,
            'profit_center': None
        }


def enhance_existing_gl_entries_with_dimensions():
    """
    Utility function to retroactively add dimensions to existing GL entries.
    This can be run once to populate dimensions for historical data.
    """
    try:
        # Get GL entries without dimensions
        gl_entries = frappe.get_all("GL Entry",
            filters={
                "job_reference": ["is", "not set"],
                "item_code": ["is", "not set"],
                "profit_center": ["is", "not set"]
            },
            fields=["name", "voucher_type", "voucher_no"],
            limit=1000  # Process in batches
        )
        
        updated_count = 0
        
        for gl_entry in gl_entries:
            if gl_entry.voucher_type and gl_entry.voucher_no:
                # Try to get dimensions from the source document
                dimensions = get_dimensions_from_document(gl_entry.voucher_type, gl_entry.voucher_no)
                
                # Update the GL Entry with dimensions
                update_fields = {}
                if dimensions.get('job_reference'):
                    update_fields['job_reference'] = dimensions['job_reference']
                if dimensions.get('item_code'):
                    update_fields['item_code'] = dimensions['item_code']
                if dimensions.get('profit_center'):
                    update_fields['profit_center'] = dimensions['profit_center']
                
                if update_fields:
                    for field, value in update_fields.items():
                        frappe.db.set_value("GL Entry", gl_entry.name, field, value)
                    updated_count += 1
        
        frappe.db.commit()
        
        return {
            "message": f"Updated {updated_count} GL entries with dimensions",
            "updated_count": updated_count
        }
        
    except Exception as e:
        frappe.logger().error(f"Error enhancing existing GL entries with dimensions: {e}")
        return {"error": str(e)}


@frappe.whitelist()
def get_gl_entries_with_dimensions(filters=None, fields=None):
    """
    Get GL Entries that have dimensions populated.
    Useful for reporting and analysis.
    """
    try:
        if not filters:
            filters = {}
        
        if not fields:
            fields = [
                "name", "posting_date", "account", "debit", "credit", 
                "job_reference", "item_code", "profit_center", 
                "voucher_type", "voucher_no"
            ]
        
        # Add filter to only get GL Entries with at least one dimension
        dimension_filters = []
        for field in ['job_reference', 'item_code', 'profit_center']:
            dimension_filters.append([field, 'is', 'set'])
        
        if dimension_filters:
            filters['or'] = dimension_filters
        
        gl_entries = frappe.get_all("GL Entry", 
            filters=filters, 
            fields=fields,
            order_by="posting_date desc, creation desc"
        )
        
        return gl_entries
        
    except Exception as e:
        frappe.logger().error(f"Error getting GL entries with dimensions: {e}")
        return []


@frappe.whitelist()
def get_dimension_wise_gl_summary(dimension_type=None, dimension_value=None, from_date=None, to_date=None):
    """
    Get summary of GL entries for a specific dimension or all dimensions.
    Useful for dimension-wise financial analysis.
    """
    try:
        filters = {}
        
        if dimension_type and dimension_value:
            filters[dimension_type] = dimension_value
        
        if from_date:
            filters['posting_date'] = ['>=', from_date]
        
        if to_date:
            if 'posting_date' in filters:
                filters['posting_date'] = ['between', [from_date or '1900-01-01', to_date]]
            else:
                filters['posting_date'] = ['<=', to_date]
        
        gl_entries = frappe.get_all("GL Entry",
            filters=filters,
            fields=[
                "job_reference", "item_code", "profit_center", 
                "account", "debit", "credit", "posting_date", 
                "voucher_type", "voucher_no"
            ]
        )
        
        # Group by dimensions and account
        summary = {}
        for entry in gl_entries:
            # Create a key based on available dimensions
            key_parts = []
            if entry.job_reference:
                key_parts.append(f"Job:{entry.job_reference}")
            if entry.item_code:
                key_parts.append(f"Item:{entry.item_code}")
            if entry.profit_center:
                key_parts.append(f"PC:{entry.profit_center}")
            
            if not key_parts:
                continue
                
            key = " | ".join(key_parts)
            account = entry.account
            
            if key not in summary:
                summary[key] = {}
            
            if account not in summary[key]:
                summary[key][account] = {
                    'total_debit': 0,
                    'total_credit': 0,
                    'entries': []
                }
            
            summary[key][account]['total_debit'] += entry.debit or 0
            summary[key][account]['total_credit'] += entry.credit or 0
            summary[key][account]['entries'].append(entry)
        
        return summary
        
    except Exception as e:
        frappe.logger().error(f"Error getting dimension-wise GL summary: {e}")
        return {}
