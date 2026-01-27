# CargoNext

**CargoNext** is a comprehensive logistics management system built on Frappe Framework. It provides end-to-end logistics solutions including transport management, warehousing, customs handling, freight operations, and job management.

## Overview

CargoNext is designed to streamline logistics operations for businesses of all sizes. It integrates seamlessly with ERPNext to provide a complete logistics management solution covering:

- **Transport Management**: Complete transport order and job management
- **Warehousing**: Warehouse job management and stock tracking
- **Customs**: Customs documentation and processing
- **Global Customs**: International customs handling
- **Sea Freight**: Ocean freight management
- **Air Freight**: Air cargo operations
- **Job Management**: Comprehensive job tracking and status management
- **Pricing Center**: Centralized pricing management
- **Logistics Sales**: Sales order integration
- **Sustainability**: Environmental impact tracking
- **Netting**: Financial netting operations

## Features

- Complete transport order lifecycle management
- Warehouse job tracking and portal access
- Multi-modal freight management (Sea, Air)
- Customs documentation and compliance
- Integration with third-party logistics providers (Lalamove, Transportify)
- Portal access for warehouse and transport jobs
- Real-time stock balance tracking
- Comprehensive job status workflows

## Requirements

- Frappe Framework (v14+)
- ERPNext
- Python 3.8 or higher

## Installation

### Using Bench (Recommended)

1. Navigate to your bench directory:
   ```bash
   cd ~/frappe-bench
   ```

2. Install the app:
   ```bash
   bench get-app logistics
   ```

3. Install the app to your site:
   ```bash
   bench --site [your-site-name] install-app logistics
   ```

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/agilasoft/logistics.git
   ```

2. Navigate to your bench apps directory:
   ```bash
   cd ~/frappe-bench/apps
   ```

3. Copy or symlink the logistics app:
   ```bash
   ln -s /path/to/logistics logistics
   ```

4. Install dependencies:
   ```bash
   bench pip install -e apps/logistics
   ```

5. Install the app to your site:
   ```bash
   bench --site [your-site-name] install-app logistics
   ```

6. Migrate the database:
   ```bash
   bench --site [your-site-name] migrate
   ```

## Post-Installation

After installation, you may need to:

1. Set up custom dimensions (if required):
   ```bash
   bench --site [your-site-name] console
   ```
   Then run:
   ```python
   from logistics.install import install_logistics_dimensions
   install_logistics_dimensions()
   ```

2. Configure portal settings for warehouse and transport job access

3. Set up integrations with third-party providers (Lalamove, Transportify, etc.)

## Dependencies

- `frappe`: Frappe Framework
- `zeep>=4.2`: SOAP client library for web service integrations

## Configuration

The app integrates with ERPNext and extends its functionality. Ensure ERPNext is installed and configured before using CargoNext.

### Portal Access

CargoNext provides portal access for:
- Warehousing Portal (`/warehousing-portal`)
- Transport Jobs (`/transport-jobs`)
- Stock Balance (`/stock-balance`)
- Warehouse Jobs (`/warehouse-jobs`)

Configure user permissions and portal settings as needed.

## Development

### Setting up Development Environment

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Running Tests

```bash
bench --site [your-site-name] run-tests --app logistics
```

## License

This project is licensed under the MIT License - see the [LICENSE](license.txt) file for details.

## Support

For support, email info@agilasoft.com or visit [www.agilasoft.com](https://www.agilasoft.com)

## Repository

- **Homepage**: https://github.com/agilasoft/logistics
- **Repository**: https://github.com/agilasoft/logistics
- **Issues**: https://github.com/agilasoft/logistics/issues

## Publisher

**Agilasoft Cloud Technologies Inc.**
- Email: info@agilasoft.com
- Website: www.agilasoft.com
