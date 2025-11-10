# Container Yard

## Overview

Container Yard (CY) is a master data document that stores information about container storage facilities, also known as container depots. Container yards are locations where containers are stored, maintained, and handled before and after vessel operations.

## Purpose

The Container Yard master is used to:
- Store information about container storage facilities
- Track container yard locations and addresses
- Manage container yard contacts
- Link container yards to ports
- Reference in Master Bill documents for origin and destination operations

## Document Structure

The Container Yard document contains the following sections:

### Basic Information

- **Code**: Unique identifier for the container yard (unique)
- **CY Name**: Full name of the container yard

### Addresses and Contacts Tab

Contains address and contact management:

- **Addresses**: HTML display of addresses linked to the container yard
- **Contacts**: HTML display of contacts linked to the container yard
- **Primary Address**: Link to primary address
- **Primary Address Display**: Display of primary address
- **Primary Contact**: Link to primary contact

## Creating a Container Yard

### Step 1: Basic Information

1. Navigate to **Sea Freight > Master > Container Yard**
2. Click **New**
3. Enter **Code** (unique identifier)
4. Enter **CY Name** (full name of the container yard)

### Step 2: Addresses and Contacts

1. Go to **Addresses and Contacts Tab**
2. The system will display linked addresses and contacts
3. To add addresses:
   - Use the Address master to create addresses
   - Link addresses to the container yard
4. To add contacts:
   - Use the Contact master to create contacts
   - Link contacts to the container yard
5. Select **Primary Address** if applicable
6. Select **Primary Contact** if applicable

### Step 3: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Code
Unique identifier for the container yard. This code is used throughout the system to reference the container yard. Must be unique across all container yards.

### CY Name
Full name of the container yard. This is the display name used in lists and reports.

### Primary Address
Link to the primary address for the container yard. This address is used as the default address in documents and reports.

### Primary Contact
Link to the primary contact person for the container yard. This contact is used as the default contact in communications.

## Usage

Container Yard is referenced in:

- **Master Bill**: 
  - Origin Container Yard (for origin operations)
  - Destination Container Yard (for destination operations)
- **Reports**: Used in container yard utilization reports
- **Operations**: Referenced in container handling operations

## Best Practices

1. **Unique Codes**: Use consistent naming conventions for container yard codes
2. **Complete Names**: Enter full container yard names for clarity
3. **Accurate Addresses**: Maintain accurate address information
4. **Contact Information**: Keep contact information up to date
5. **Port Association**: Ensure container yards are associated with correct ports (via address or other means)
6. **Regular Updates**: Review and update container yard information regularly

## Address Management

Container yards can have multiple addresses:

1. Create addresses in the Address master
2. Link addresses to the container yard
3. Set one address as the primary address
4. The primary address is used as the default in documents

## Contact Management

Container yards can have multiple contacts:

1. Create contacts in the Contact master
2. Link contacts to the container yard
3. Set one contact as the primary contact
4. The primary contact is used as the default in communications

## Related Documents

- **Master Bill**: References container yards for origin and destination
- **Address**: Linked addresses for the container yard
- **Contact**: Linked contacts for the container yard

## Next Steps

- Learn about [Master Bill](master-bill.md) operations
- Understand [Cargo Terminal Operator](cargo-terminal-operator.md) management
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

