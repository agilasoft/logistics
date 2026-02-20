# Transit Entry Routing Implementation Guide

## 📋 Overview

This document explains the **Automatic Routing Creation for Transit Entry Type** feature in the Logistics system. When an Air Booking or Air Shipment is created with a **Transit** entry type (which maps to "Transshipment" in the system), the system automatically creates routing legs to help track the cargo journey through intermediate ports.

---

## 🎯 What is Transit Entry Routing?

**Transit Entry Routing** automatically creates routing legs when cargo is marked as transit/transshipment. This eliminates manual routing setup and ensures proper tracking of cargo that passes through intermediate airports before reaching its final destination.

### Real-World Use Cases

1. **Multi-Leg Journeys**: Cargo traveling from Origin → Transit Airport → Final Destination
2. **Transshipment Tracking**: Track cargo that changes flights/airlines at intermediate airports
3. **Compliance & Documentation**: Ensure proper routing documentation for customs and regulatory purposes
4. **Operational Visibility**: Provide clear visibility of the complete cargo journey
5. **Cost Allocation**: Help allocate costs across different legs of the journey

---

## 🚀 How to Use This Feature

### Step-by-Step User Guide

#### **Scenario 1: Creating Air Booking with Transit Entry Type**

1. **Create a New Air Booking**
   - Navigate to: **Air Freight → Air Booking → New**
   - Fill in the basic booking details (Booking Date, Customer, etc.)

2. **Set Entry Type to Transit**
   - In the **Booking Details** section, locate the **Entry Type** field
   - Select **"Transshipment"** from the dropdown
     - Note: "Transshipment" is the system term for Transit entry type
     - This maps from "Transit" in Sales Quote

3. **Fill Required Port Information**
   - **Origin Airport**: Select the origin UNLOCO code
   - **Destination Port**: Select the final destination UNLOCO code
   - **ETD**: Enter Estimated Time of Departure
   - **ETA**: Enter Estimated Time of Arrival

4. **Save the Document**
   - Click **Save** button
   - The system automatically creates a routing leg in the **Routing** tab

5. **View Created Routing**
   - Navigate to the **Routing** tab
   - You will see a routing leg automatically created with:
     - **Leg Order**: 1
     - **Mode**: AIR
     - **Type**: Main
     - **Status**: Planned
     - **Load Port**: Your origin port
     - **Discharge Port**: Your destination port
     - **ETD/ETA**: Dates from the main document

6. **Modify Routing as Needed**
   - You can add additional legs if cargo transits through intermediate airports
   - Edit the created leg to add flight numbers, carriers, or other details
   - Add more legs by clicking **Add Row** in the Routing Legs table

#### **Scenario 2: Creating from Sales Quote**

1. **Create Sales Quote with Transit Entry Type**
   - In Sales Quote, set **Air Entry Type** to **"Transit"**
   - Fill in other required details

2. **Create Air Booking from Sales Quote**
   - Create a new Air Booking
   - Link it to the Sales Quote
   - Click **"Fetch Quotations"** button
   - The system will:
     - Map "Transit" from Sales Quote to "Transshipment" in Air Booking
     - Automatically create routing when the document is saved

3. **Routing is Automatically Created**
   - After saving, check the **Routing** tab
   - Routing leg is automatically populated

#### **Scenario 3: Converting Air Booking to Air Shipment**

1. **Create Air Booking with Transit Entry Type**
   - Follow steps from Scenario 1
   - Ensure routing is created

2. **Convert to Air Shipment**
   - Click **"Convert to Shipment"** button
   - The routing legs are automatically copied to Air Shipment
   - If Air Shipment doesn't have routing and entry_type is "Transshipment", routing is created automatically

---

## 🔧 Technical Implementation

### When Routing is Created

The system automatically creates routing in the following scenarios:

1. **On Document Save**: When Air Booking or Air Shipment is saved with `entry_type = "Transshipment"`
2. **Only if Empty**: Routing is only created if `routing_legs` table is empty (prevents overwriting existing routing)
3. **Requires Ports**: Both `origin_port` and `destination_port` must be set

### Implementation Details

#### **Air Booking Implementation**

**Location**: `logistics/air_freight/doctype/air_booking/air_booking.py`

**Method**: `create_routing_for_transit_entry()`

**Called From**: `validate()` method

```python
def create_routing_for_transit_entry(self):
    """
    Automatically create routing legs when entry_type is Transshipment (Transit).
    Creates a main routing leg from origin to destination if routing_legs is empty.
    """
    # Only create routing if entry_type is Transshipment
    if self.entry_type != "Transshipment":
        return
    
    # Only create routing if routing_legs is empty
    routing_legs = getattr(self, "routing_legs", []) or []
    if routing_legs:
        return
    
    # Require origin and destination ports
    if not self.origin_port or not self.destination_port:
        return
    
    # Create main routing leg
    leg_data = {
        "leg_order": 1,
        "mode": "AIR",
        "type": "Main",
        "status": "Planned",
        "load_port": self.origin_port,
        "discharge_port": self.destination_port,
        "etd": self.etd,
        "eta": self.eta,
    }
    
    # Set carrier information if available
    if self.airline:
        leg_data["carrier_type"] = "Airline"
        leg_data["carrier"] = self.airline
    
    # Append the routing leg
    self.append("routing_legs", leg_data)
```

#### **Air Shipment Implementation**

**Location**: `logistics/air_freight/doctype/air_shipment/air_shipment.py`

**Method**: `create_routing_for_transit_entry()`

**Called From**: `validate()` method

Same implementation as Air Booking for consistency.

### Entry Type (Unified)

Entry types are aligned across Sales Quote, Air Booking, and Air Shipment. No mapping needed.

**Options** (industry standard): Direct, Transit, Transshipment, ATA Carnet

**Routing trigger**: Both "Transit" and "Transshipment" trigger automatic routing creation.

---

## 📊 Routing Leg Structure

### Automatically Created Fields

When routing is automatically created, the following fields are populated:

| Field | Value | Description |
|-------|-------|-------------|
| **Leg Order** | 1 | Sequence number of the leg |
| **Mode** | AIR | Transportation mode |
| **Type** | Main | Leg type (Main/Pre-carriage/On-forwarding) |
| **Status** | Planned | Current status of the leg |
| **Load Port** | Origin Port | Port where cargo is loaded |
| **Discharge Port** | Destination Port | Port where cargo is discharged |
| **ETD** | Document ETD | Estimated Time of Departure |
| **ETA** | Document ETA | Estimated Time of Arrival |
| **Carrier Type** | Airline | Type of carrier (if airline is set) |
| **Carrier** | Airline Name | Specific carrier/airline (if airline is set) |

### Fields You Can Manually Add

After routing is created, you can manually add:

- **Flight No**: Flight number for the leg
- **Vessel**: For sea freight (not applicable for air)
- **Voyage No**: For sea freight (not applicable for air)
- **ATD**: Actual Time of Departure
- **ATA**: Actual Time of Arrival
- **Notes**: Additional notes about the leg
- **Charter Route**: If this is a charter route

---

## 💡 Examples

### Example 1: Simple Transit Routing

**Scenario**: Cargo from New York (JFK) to Tokyo (NRT) via Dubai (DXB)

**Steps**:
1. Create Air Booking
2. Set Entry Type: **Transshipment**
3. Origin Port: **USNYC** (New York)
4. Destination Port: **JPTYO** (Tokyo)
5. Save document

**Result**: 
- System creates 1 routing leg: JFK → NRT
- You can manually add a second leg: JFK → DXB (Leg 1), DXB → NRT (Leg 2)

### Example 2: Multi-Leg Transit

**Scenario**: Cargo with known transit points

**Steps**:
1. Create Air Booking with Transit entry type
2. System creates initial leg: Origin → Destination
3. Manually modify routing:
   - **Leg 1**: Origin → Transit Airport (Flight: AA123)
   - **Leg 2**: Transit Airport → Destination (Flight: JL456)

**Result**: Complete routing with all transit points documented

### Example 3: From Sales Quote

**Scenario**: Creating Air Booking from Sales Quote with Transit entry type

**Steps**:
1. Sales Quote has **Air Entry Type** = "Transit"
2. Create Air Booking and link to Sales Quote
3. Click **"Fetch Quotations"**
4. System maps "Transit" → "Transshipment"
5. Save Air Booking

**Result**: Routing automatically created with mapped entry type

---

## ✅ Validation Rules

The system enforces the following rules:

1. **Entry Type Check**: Routing is only created when `entry_type = "Transshipment"`
2. **Empty Routing**: Routing is only created if `routing_legs` table is empty
3. **Required Ports**: Both `origin_port` and `destination_port` must be set
4. **No Overwrite**: Existing routing is never overwritten by automatic creation

---

## 🔍 Troubleshooting

### Routing Not Created?

**Check the following**:

1. **Entry Type**: Ensure `entry_type` is set to **"Transshipment"**
   - If using Sales Quote, ensure "Transit" is selected (it maps to Transshipment)

2. **Ports Required**: Both Origin Port and Destination Port must be filled
   - Check that UNLOCO codes are valid

3. **Existing Routing**: If routing already exists, automatic creation is skipped
   - Clear existing routing legs if you want automatic creation

4. **Document Status**: Ensure document is saved (not just draft)
   - Routing is created during `validate()` which runs on save

### Routing Created But Missing Information?

**Common Issues**:

1. **Missing Carrier**: If airline is not set on the document, carrier fields won't be populated
   - Solution: Set the Airline field, or manually add carrier to routing leg

2. **Missing Dates**: If ETD/ETA are not set, routing leg will have empty dates
   - Solution: Fill ETD/ETA on the main document before saving

3. **Wrong Ports**: If origin/destination ports are incorrect, routing will reflect those
   - Solution: Correct ports on main document, then delete and recreate routing

---

## 🎨 User Interface

### Where to Find Routing

1. **Air Booking Form**:
   - Navigate to **Routing** tab
   - View **Routing Legs** table

2. **Air Shipment Form**:
   - Navigate to **Routing** tab
   - View **Routing Legs** table

### Visual Indicators

- **Leg Order**: Shows sequence (1, 2, 3, etc.)
- **Status**: Color-coded status (Planned/Confirmed/On-hold)
- **Mode**: Shows AIR or SEA icon
- **Type**: Indicates Main/Pre-carriage/On-forwarding

---

## 📚 Related Documentation

- [Excess Weight Volume Implementation](./EXCESS_WEIGHT_VOLUME_IMPLEMENTATION.md)
- [Routing Tab Design](./docs/ROUTING_TAB_DESIGN.md)
- [Air Booking Volume and Weight Analysis](./AIR_BOOKING_VOLUME_WEIGHT_ANALYSIS.md)

---

## ❓ Frequently Asked Questions

### Q: Why is routing only created for "Transshipment" entry type?

**A**: Transshipment (Transit) entry type indicates cargo that passes through intermediate ports. Direct shipments don't require multi-leg routing, so automatic creation is only for transit scenarios.

### Q: Can I disable automatic routing creation?

**A**: Currently, automatic routing creation cannot be disabled. However, it only creates routing if the routing_legs table is empty, so existing routing is never overwritten.

### Q: What if I need more than one routing leg?

**A**: The system creates the first leg automatically. You can manually add additional legs by clicking "Add Row" in the Routing Legs table.

### Q: Does this work for Sea Freight?

**A**: Currently, this feature is implemented for Air Booking and Air Shipment only. Sea Freight routing creation can be added in a future enhancement.

### Q: What happens when I convert Air Booking to Air Shipment?

**A**: All routing legs are automatically copied from Air Booking to Air Shipment. If Air Shipment doesn't have routing and entry_type is "Transshipment", routing is also created automatically.

### Q: Can I modify the automatically created routing?

**A**: Yes! The automatically created routing leg is fully editable. You can modify any field, add flight numbers, change status, or add additional legs.

### Q: What if I change entry_type after routing is created?

**A**: Changing entry_type does not delete existing routing. Routing remains in place. If you delete routing and change entry_type back to "Transshipment", routing will be recreated on save.

---

## 🔄 Version History

- **v1.0** (2025-02-10): Initial implementation
  - Added automatic routing creation to Air Booking
  - Added automatic routing creation to Air Shipment
  - Entry type mapping from Sales Quote
  - Automatic routing on document save

---

## 👥 Support

For questions or issues related to Transit Entry Routing:
- Contact the development team
- Refer to technical documentation
- Check system logs for validation errors

---

## 📝 Notes for Developers

### Important Considerations:

1. **Entry Type Mapping**: "Transit" from Sales Quote maps to "Transshipment" in Air Booking
2. **Validation Timing**: Routing is created during `validate()`, which runs before save
3. **No Overwrite**: Always check if routing_legs is empty before creating
4. **Port Validation**: Ensure ports are valid UNLOCO codes before creating routing

### Testing Scenarios:

Test the following scenarios:
1. Create Air Booking with Transit entry type → Routing created
2. Create Air Booking with Direct entry type → No routing created
3. Create Air Booking with existing routing → No overwrite
4. Create Air Booking without ports → No routing created
5. Convert Air Booking to Air Shipment → Routing copied
6. Create Air Shipment directly with Transit → Routing created

### Future Enhancements:

Potential improvements:
1. **Configurable Settings**: Allow users to enable/disable automatic routing creation
2. **Sea Freight Support**: Extend to Sea Booking and Sea Shipment
3. **Transit Port Detection**: Automatically detect transit ports from flight schedules
4. **Multi-Leg Creation**: Automatically create multiple legs based on known transit points
5. **Template-Based Routing**: Use routing templates for common transit routes

---

**Last Updated**: February 10, 2025  
**Status**: ✅ Implemented and Active  
**Version**: 1.0
