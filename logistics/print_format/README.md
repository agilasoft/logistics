# Default Print Formats

This module provides BIR-compliant, compact, and modern print formats for standard ERPNext doctypes.

## Print Formats Included

### 1. BIR Sales Invoice
- **Location**: `logistics/print_format/sales_invoice/`
- **Format Name**: "BIR Sales Invoice"
- **DocType**: Sales Invoice
- **Features**:
  - BIR-compliant layout with TIN information
  - Compact design with modern styling
  - Includes all required invoice details
  - Tax breakdown section
  - Signature sections for prepared by and received by

### 2. BIR Purchase Invoice
- **Location**: `logistics/print_format/purchase_invoice/`
- **Format Name**: "BIR Purchase Invoice"
- **DocType**: Purchase Invoice
- **Features**:
  - BIR-compliant layout with TIN information
  - Compact design with modern styling
  - Includes all required invoice details
  - Tax breakdown section
  - Signature sections for prepared by and approved by

## Installation

The print formats are automatically installed during the app's `after_install` hook. They can also be manually installed using:

```bash
# Install all print formats
python3 logistics/print_format/install_all_print_formats.py <site_name>

# Install individual formats
python3 logistics/print_format/sales_invoice/install_print_format.py <site_name>
python3 logistics/print_format/purchase_invoice/install_print_format.py <site_name>
```

## Usage

After installation, the print formats will be available in the Print menu for Sales Invoice and Purchase Invoice documents:

1. Open a Sales Invoice or Purchase Invoice
2. Click on "Print" button
3. Select "BIR Sales Invoice" or "BIR Purchase Invoice" from the print format dropdown

## Design Features

- **Compact Layout**: Optimized use of space with efficient grid-based layouts
- **Modern Design**: Clean, professional styling with proper typography
- **BIR Compliance**: Includes all required BIR fields (TIN, Branch Code, etc.)
- **Print Optimized**: Designed for A4 paper size with proper margins
- **Responsive**: Adapts to different screen sizes and print preview

## Customization

The print formats use Jinja2 templating. To customize:

1. Edit the HTML files in their respective directories
2. Run the installation script again to update the print format
3. The changes will be reflected in existing documents

## Requirements

- Frappe Framework
- ERPNext (for Sales Invoice and Purchase Invoice doctypes)
- BIR custom fields (TIN, Branch Code) - should be set up via BIR CAS app

## File Structure

```
logistics/print_format/
├── __init__.py
├── README.md
├── install_all_print_formats.py
├── sales_invoice/
│   ├── sales_invoice.html
│   ├── sales_invoice.json
│   └── install_print_format.py
└── purchase_invoice/
    ├── purchase_invoice.html
    ├── purchase_invoice.json
    └── install_print_format.py
```


