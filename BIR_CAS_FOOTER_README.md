# BIR CAS Footer Script for ERPNext Letter Head

This script fetches BIR CAS (Bureau of Internal Revenue Computerized Accounting System) details from the **BIR CAS Settings** doctype and displays them in the letter head footer.

## Quick Start

1. **Copy the script** from one of the following files:
   - **`bir_cas_footer_script_simple.html`** (⭐ RECOMMENDED - Most reliable, tested approach)
   - `bir_cas_footer_script_compact.html` (Compact version)
   - `bir_cas_footer_script.html` (Full-featured version with extensive formatting)

2. **Go to ERPNext**: Letter Head → Select/Create a Letter Head

3. **Paste the script** into the **Footer** field

4. **Save** the Letter Head

**Note**: Open the script file and copy everything starting from the first `{%` to the last `%}` (excluding HTML comments if you prefer a cleaner footer field).

## Required BIR CAS Settings Doctype Fields

The script expects the following fields in your **BIR CAS Settings** doctype:

### Required Fields
- `company` (Link to Company) - Links settings to a specific company
- `tin` (Data) - Tax Identification Number
- `branch_code` (Data) - Branch Code (optional)

### Recommended Fields
- `company_name` (Data) - Company name for footer display
- `business_address` (Small Text) - Business address
- `city` (Data) - City
- `state` (Data) - State/Province
- `postal_code` (Data) - Postal/ZIP code
- `cas_number` (Data) - CAS Registration Number
- `accreditation_number` (Data) - BIR Accreditation Number
- `accreditation_date` (Date) - Date of accreditation
- `contact_number` (Data) - Phone number
- `email` (Data) - Email address
- `website` (Data) - Website URL
- `bir_authorized_representative` (Data) - Authorized representative name
- `footer_note` (Small Text) - Additional footer note

## Script Versions

### Simple Version (`bir_cas_footer_script_simple.html`) ⭐ RECOMMENDED
- **Most reliable** - Uses proven ERPNext Jinja2 patterns
- Clean, straightforward code
- Shows all essential BIR CAS details
- Falls back gracefully to Company doctype if BIR CAS Settings not found
- **Best choice for production use**

### Compact Version (`bir_cas_footer_script_compact.html`)
- Minimal code, easier to customize
- Shows essential BIR CAS details
- Falls back to Company doctype if BIR CAS Settings not found
- Good for quick implementation

### Full Version (`bir_cas_footer_script.html`)
- Complete feature set with extensive formatting
- More detailed styling and layout options
- Additional fields and fallback options
- Better error handling
- Best for custom requirements

## Customization

You can customize the script by:

1. **Changing field names**: If your BIR CAS Settings doctype uses different field names, update them in the script
2. **Modifying styling**: Adjust the inline CSS styles (font-size, colors, margins, etc.)
3. **Adding/removing fields**: Add or remove fields as needed
4. **Changing layout**: Modify the HTML structure to match your requirements

## Example Output

The footer will display something like:

```
Company Name
Business Address
City, State Postal Code

TIN: 123-456-789-000-001
CAS No.: CAS-2024-001
Accreditation No.: ACC-2024-001
Tel: +63 2 1234 5678
Email: info@company.com
```

## Troubleshooting

### Script not showing data
- Ensure **BIR CAS Settings** doctype exists
- Verify a record exists for the company in the document
- Check field names match between doctype and script

### Fallback to Company details
- The script automatically falls back to Company doctype if BIR CAS Settings not found
- Ensure Company has `tin` and `branch_code` fields populated

### Formatting issues
- Adjust inline CSS styles in the script
- Test with different document types (Sales Invoice, Purchase Invoice, etc.)
- Check print preview to ensure proper formatting

## Notes

- The script uses Jinja2 template syntax (ERPNext standard)
- All fields are optional - script will skip empty fields
- The script automatically handles company-specific settings
- Compatible with ERPNext v13+

## Support

For issues or questions, refer to:
- ERPNext Documentation: https://docs.erpnext.com
- BIR CAS Documentation: BIR Philippines official website

