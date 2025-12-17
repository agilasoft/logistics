#!/usr/bin/env python3
"""
Export Address Client Script to file system for version control
"""
import frappe
import json
import os

def export_address_client_script():
    frappe.init()
    frappe.connect()
    
    # Find all Client Scripts for Address
    client_scripts = frappe.get_all(
        'Client Script',
        filters={'dt': 'Address'},
        fields=['name', 'view', 'enabled', 'script', 'module', 'modified', 'modified_by']
    )
    
    if not client_scripts:
        print("No Client Scripts found for Address")
        return
    
    # Create client_scripts directory if it doesn't exist
    client_scripts_dir = os.path.join(
        os.path.dirname(__file__),
        'logistics',
        'transport',
        'client_scripts'
    )
    os.makedirs(client_scripts_dir, exist_ok=True)
    
    for script in client_scripts:
        print(f"Exporting Client Script: {script['name']}")
        
        # Get full document
        doc = frappe.get_doc('Client Script', script['name'])
        
        # Create JSON file for the client script (convert to dict and handle datetime)
        script_data = doc.as_dict()
        # Convert datetime to string for JSON serialization
        if script_data.get('modified'):
            script_data['modified'] = str(script_data['modified'])
        if script_data.get('creation'):
            script_data['creation'] = str(script_data['creation'])
        
        # Save to file
        filename = f"address_{script['view'].lower()}.json"
        filepath = os.path.join(client_scripts_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(script_data, f, indent=2)
        
        print(f"  ✓ Exported to: {filepath}")
    
    print(f"\n✅ Exported {len(client_scripts)} Client Script(s) to {client_scripts_dir}")
    print("You can now commit these files to GitHub for migration.")

if __name__ == '__main__':
    export_address_client_script()

