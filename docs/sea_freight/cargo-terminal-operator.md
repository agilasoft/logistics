# Cargo Terminal Operator

## Overview

Cargo Terminal Operator (CTO) is a master data document that stores information about terminal operators that handle cargo at ports and terminals. CTOs manage terminal operations including cargo handling, storage, and vessel operations.

## Purpose

The Cargo Terminal Operator master is used to:
- Store information about terminal operators
- Track terminal operator codes and names
- Indicate which transport modes the operator handles (Air, Sea, Rail, Road)
- Reference in Master Bill documents for origin and destination terminal operations
- Link to Shipping Line records

## Document Structure

The Cargo Terminal Operator document contains the following sections:

### Basic Information

- **Code**: Unique identifier for the terminal operator
- **CTO Name**: Full name of the cargo terminal operator

### Available For

Checkboxes indicating which transport modes the operator handles:

- **Air**: Handles air cargo operations
- **Sea**: Handles sea cargo operations
- **Rail**: Handles rail cargo operations
- **Road**: Handles road cargo operations

## Creating a Cargo Terminal Operator

### Step 1: Basic Information

1. Navigate to **Sea Freight > Master > Cargo Terminal Operator**
2. Click **New**
3. Enter **Code** (unique identifier)
4. Enter **CTO Name** (full name of the terminal operator)

### Step 2: Transport Modes

1. Check the appropriate transport modes:
   - **Air**: If the operator handles air cargo
   - **Sea**: If the operator handles sea cargo
   - **Rail**: If the operator handles rail cargo
   - **Road**: If the operator handles road cargo
2. Check all applicable modes

### Step 3: Save

1. Review all information
2. Click **Save**

## Key Fields Explained

### Code
Unique identifier for the cargo terminal operator. This code is used throughout the system to reference the terminal operator.

### CTO Name
Full name of the cargo terminal operator. This is the display name used in lists and reports.

### Available For
Checkboxes indicating which transport modes the operator handles. This helps filter operators by transport mode in selection lists.

## Usage

Cargo Terminal Operator is referenced in:

- **Master Bill**: 
  - Origin CTO (for origin terminal operations)
  - Destination CTO (for destination terminal operations)
- **Shipping Line**: Linked in CTOs table to associate operators with shipping lines
- **Reports**: Used in terminal operator reports
- **Operations**: Referenced in terminal handling operations

## Transport Mode Selection

The transport mode checkboxes help:

- Filter operators by transport mode in selection lists
- Identify multi-modal operators
- Ensure correct operator selection for specific operations
- Support integrated operations across transport modes

## Best Practices

1. **Unique Codes**: Use consistent naming conventions for CTO codes
2. **Complete Names**: Enter full terminal operator names for clarity
3. **Accurate Transport Modes**: Check all applicable transport modes
4. **Regular Updates**: Review and update CTO information regularly
5. **Multi-Modal Support**: Indicate if operator handles multiple transport modes

## Multi-Modal Operators

Some terminal operators handle multiple transport modes:

1. Check all applicable transport mode checkboxes
2. These operators will appear in selection lists for all checked modes
3. Useful for integrated logistics operations

## Related Documents

- **Master Bill**: References CTOs for origin and destination
- **Shipping Line**: Links CTOs in CTOs table
- **Container Yard**: May be associated with CTOs
- **Container Freight Station**: May be associated with CTOs

## Next Steps

- Learn about [Master Bill](master-bill.md) operations
- Understand [Shipping Line](shipping-line.md) management
- Review [Master Data](master-data.md) setup

---

*For setup instructions, refer to the [Setup Guide](setup.md).*

