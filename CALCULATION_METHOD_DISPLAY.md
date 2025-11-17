# Calculation Method Display Guide

## Overview
This document explains how **Base Plus Additional** and **First Plus Additional** calculation methods are displayed in Warehouse Job Charges, Periodic Billing, and Sales Invoice.

---

## 1. Warehouse Job Charges

### Table Structure:
- **Item Code**: Charge item
- **Item Name**: Description
- **UOM**: Unit of measure (Day, CBM, KG, etc.)
- **Quantity**: Billing quantity (calculated from job)
- **Rate**: Unit rate from contract
- **Total**: Final calculated amount
- **Calculation Notes**: Detailed breakdown (Long Text field)

### Display Examples:

#### **Base Plus Additional** Method:
```
Item Code: Storage Charge
Item Name: Storage Charge (Volume - Daily Volume)
UOM: CBM
Quantity: 1.0
Rate: 90.00
Total: 90.00
```

**Calculation Notes:**
```
Warehouse Job Charge Calculation (Contract Generated):
  • Warehouse Job: WHJ-00001
  • Job Type: Inbound
  • Period: 2025-01-01 to 2025-01-05
  • Calculation Method: Base Plus Additional
  • Billing Method: Per Volume
  • UOM: CBM
  • Rate per CBM: 10.00
  • Actual Billing Quantity: 5.0
  • Base Amount: 50.00
  • Additional (4.0 units @ 10.00): 40.00
  • Total: 90.00
  • Display: Qty = 1, Rate = 90.00, Total = 90.00
  • Currency: USD
```

**How it works:**
- **Actual Billing Quantity** = 5.0 (from job)
- **Unit Rate** = 10.00 (from contract)
- **Base Amount** = 50.00 (from contract)
- **Additional** = 10.00 × (5.0 - 1) = 40.00
- **Total** = 50.00 + 40.00 = 90.00
- **Display:**
  - **Quantity** = 1.0 (simplified)
  - **Rate** = 90.00 (total amount)
  - **Total** = 90.00

---

#### **First Plus Additional** Method:
```
Item Code: Handling Charge
Item Name: Handling Charge (Per Piece)
UOM: Piece
Quantity: 1.0
Rate: 30.00
Total: 30.00
```

**Calculation Notes:**
```
Warehouse Job Charge Calculation (Contract Generated):
  • Warehouse Job: WHJ-00002
  • Job Type: Outbound
  • Period: 2025-01-01 to 2025-01-03
  • Calculation Method: First Plus Additional
  • Billing Method: Per Piece
  • UOM: Piece
  • Rate per Piece: 5.00
  • Actual Billing Quantity: 8.0
  • First 3 units: 5.00
  • Additional (5.0 units @ 5.00): 25.00
  • Total: 30.00
  • Display: Qty = 1, Rate = 30.00, Total = 30.00
  • Currency: USD
```

**How it works:**
- **Actual Billing Quantity** = 8.0 (from job)
- **Unit Rate** = 5.00 (from contract)
- **Minimum Quantity** = 3.0 (from contract)
- **First 3 units** = 5.00 (flat rate for first batch)
- **Additional** = 5.00 × (8.0 - 3.0) = 25.00
- **Total** = 5.00 + 25.00 = 30.00
- **Display:**
  - **Quantity** = 1.0 (simplified)
  - **Rate** = 30.00 (total amount)
  - **Total** = 30.00

---

## 2. Periodic Billing Charges

### Table Structure:
- **Item**: Charge item
- **Item Name**: Description
- **UOM**: Unit of measure
- **Quantity**: Billing quantity (aggregated from period)
- **Rate**: Unit rate from contract
- **Total**: Final calculated amount
- **Calculation Notes**: Detailed breakdown

### Display Examples:

#### **Base Plus Additional** Method:
```
Item: Storage Charge
Item Name: Storage Charge (Volume - Daily Volume)
UOM: CBM
Quantity: 1.0
Rate: 1,540.00
Total: 1,540.00
```

**Calculation Notes:**
```
Storage Charge Calculation:
  • Handling Unit: HU-001
  • Period: 2025-01-01 to 2025-01-31
  • Billing Method: Per Volume
  • Calculation Method: Base Plus Additional
  • UOM: CBM
  • Rate per CBM: 10.00
  • Actual Billing Quantity: 150.0
  • Base Amount: 50.00
  • Additional (149.0 units @ 10.00): 1,490.00
  • Total: 1,540.00
  • Display: Qty = 1, Rate = 1,540.00, Total = 1,540.00
  • Storage Location: A-01-01
  • Handling Unit Type: Pallet
  • Storage Type: Ambient
```

**How it works:**
- **Actual Billing Quantity** = 150.0 (aggregated volume for the period)
- **Unit Rate** = 10.00 (from contract)
- **Base Amount** = 50.00 (from contract)
- **Additional** = 10.00 × (150.0 - 1) = 1,490.00
- **Total** = 50.00 + 1,490.00 = 1,540.00
- **Display:**
  - **Quantity** = 1.0 (simplified)
  - **Rate** = 1,540.00 (total amount)
  - **Total** = 1,540.00

---

#### **First Plus Additional** Method:
```
Item: Handling Charge
Item Name: Handling Charge (Per Piece)
UOM: Piece
Quantity: 1.0
Rate: 115.00
Total: 115.00
```

**Calculation Notes:**
```
Job Charge Calculation:
  • Period: 2025-01-01 to 2025-01-31
  • Calculation Method: First Plus Additional
  • Billing Method: Per Piece
  • UOM: Piece
  • Rate per Piece: 5.00
  • Actual Billing Quantity: 25.0
  • First 3 units: 5.00
  • Additional (22.0 units @ 5.00): 110.00
  • Total: 115.00
  • Display: Qty = 1, Rate = 115.00, Total = 115.00
```

**How it works:**
- **Actual Billing Quantity** = 25.0 (aggregated pieces for the period)
- **Unit Rate** = 5.00 (from contract)
- **Minimum Quantity** = 3.0 (from contract)
- **First 3 units** = 5.00 (flat rate)
- **Additional** = 5.00 × (25.0 - 3.0) = 110.00
- **Total** = 5.00 + 110.00 = 115.00
- **Display:**
  - **Quantity** = 1.0 (simplified)
  - **Rate** = 115.00 (total amount)
  - **Total** = 115.00

---

## 3. Sales Invoice

### Table Structure (Sales Invoice Item):
- **Item Code**: Charge item
- **Item Name**: Description
- **UOM**: Unit of measure
- **Qty**: Quantity (same as source)
- **Rate**: Unit rate (same as source)
- **Amount**: Total amount (same as source)
- **Description**: Can include calculation notes

### Display Examples:

#### **Base Plus Additional** Method:
```
Item Code: Storage Charge
Item Name: Storage Charge (Volume - Daily Volume)
UOM: CBM
Qty: 1.0
Rate: 1,540.00
Amount: 1,540.00
Description: [Calculation notes can be included here]
```

**How it works:**
- **Qty** = 1.0 (copied from Periodic Billing Charges - simplified display)
- **Rate** = 1,540.00 (copied from Periodic Billing Charges Total)
- **Amount** = 1,540.00 (copied from Periodic Billing Charges Total)
- The calculation breakdown is preserved in the source charge's calculation_notes

---

#### **First Plus Additional** Method:
```
Item Code: Handling Charge
Item Name: Handling Charge (Per Piece)
UOM: Piece
Qty: 1.0
Rate: 115.00
Amount: 115.00
Description: [Calculation notes can be included here]
```

**How it works:**
- **Qty** = 1.0 (copied from Periodic Billing Charges - simplified display)
- **Rate** = 115.00 (copied from Periodic Billing Charges Total)
- **Amount** = 115.00 (copied from Periodic Billing Charges Total)
- The calculation breakdown is preserved in the source charge's calculation_notes

---

## Key Points:

### 1. **Quantity Field Display:**
   - **Per Unit, Fixed Amount, Percentage**: Shows actual billing quantity
   - **Base Plus Additional, First Plus Additional**: Shows **1.0** (simplified display)
   - Actual billing quantity is preserved in calculation notes

### 2. **Rate Field Display:**
   - **Per Unit, Fixed Amount, Percentage**: Shows unit rate from contract
   - **Base Plus Additional, First Plus Additional**: Shows **computed total amount** (simplified display)
   - Actual unit rate is preserved in calculation notes

### 3. **Total/Amount Field Display:**
   - Always shows the **final calculated amount** after applying the calculation method
   - For Base Plus Additional: Base + (Rate × (Qty - 1))
   - For First Plus Additional: First Rate + (Rate × (Qty - Min Qty))
   - For Base Plus Additional and First Plus Additional: Rate = Total (same value)

### 4. **Calculation Notes:**
   - Contains the **full breakdown** showing:
     - Base amount (for Base Plus Additional)
     - First batch amount (for First Plus Additional)
     - Additional units calculation
     - Final total
   - This is the **source of truth** for understanding the calculation

### 5. **Visual Representation:**

**Base Plus Additional:**
```
Display: Qty: 1.0    Rate: 90.00    Total: 90.00
         ↓
Calculation: Base (50.00) + Additional (4 × 10.00) = 90.00
Actual Billing Qty: 5.0 CBM
```

**First Plus Additional:**
```
Display: Qty: 1.0    Rate: 30.00    Total: 30.00
         ↓
Calculation: First 3 (5.00) + Additional (5 × 5.00) = 30.00
Actual Billing Qty: 8.0 pieces
```

---

## Recommendations for UI Display:

1. **Add a tooltip or info icon** next to Total field showing the breakdown
2. **Color-code or highlight** when calculation method is not "Per Unit"
3. **Show calculation method** in the item description or as a badge
4. **Make calculation_notes field** easily accessible (expandable section)

---

## Implementation Status:

✅ Calculation logic implemented in `_apply_calculation_method()`
✅ Calculation notes generated in `_generate_comprehensive_calculation_notes_for_contract_charge()`
✅ Fields stored correctly in Warehouse Job Charges
✅ Fields flow to Periodic Billing Charges
✅ Fields flow to Sales Invoice

---

## Example Scenarios:

### Scenario 1: Base Plus Additional - Storage Charge
- Contract: Base = 50.00, Rate = 10.00 per CBM
- Job Volume: 5.0 CBM
- **Calculation:** Base (50.00) + Additional (4 × 10.00) = 90.00
- **Display:**
  - Qty: 1.0
  - Rate: 90.00
  - Total: 90.00

### Scenario 2: First Plus Additional - Handling Charge
- Contract: First 3 pieces = 5.00, Additional = 5.00 per piece
- Job Pieces: 8 pieces
- **Calculation:** First 3 (5.00) + Additional (5 × 5.00) = 30.00
- **Display:**
  - Qty: 1.0
  - Rate: 30.00
  - Total: 30.00

