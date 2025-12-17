import frappe

def remove_address_custom_scripts():
    # Check for Customize Form
    try:
        customize = frappe.get_doc('Customize Form', {'doc_type': 'Address'})
        if customize.script:
            print(f'Found custom script in Customize Form (length: {len(customize.script)})')
            customize.script = ''
            customize.save()
            frappe.db.commit()
            print('✅ Custom script removed from Customize Form')
        else:
            print('No custom script in Customize Form')
    except frappe.DoesNotExistError:
        print('No Customize Form found for Address')
    except Exception as e:
        print(f'Error with Customize Form: {e}')
    
    # Check for Client Script
    try:
        client_scripts = frappe.get_all('Client Script', filters={'dt': 'Address'}, fields=['name', 'script'])
        if client_scripts:
            print(f'Found {len(client_scripts)} Client Script(s) for Address:')
            for cs in client_scripts:
                print(f'  - {cs.name} (script length: {len(cs.script) if cs.script else 0})')
                frappe.delete_doc('Client Script', cs.name, force=1)
            frappe.db.commit()
            print('✅ Client Scripts removed')
        else:
            print('No Client Scripts found for Address')
    except Exception as e:
        print(f'Error checking Client Script: {e}')
    
    print('\n✅ Done! Custom scripts have been removed.')
    print('Please refresh your browser to see the changes.')

