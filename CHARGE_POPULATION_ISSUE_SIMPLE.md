# Why Charges from Sales Quote Don't Populate to Bookings and Orders

## The Problem

When you create a Booking (Air Booking, Sea Booking) or Order (Transport Order) from a Sales Quote, **not all charges are being copied over**. Only charges that match the main service type are transferred.

## What's Happening

### Example:
Your Sales Quote has:
- 5 Air freight charges
- 3 Customs charges  
- 2 Warehousing charges

When you create an **Air Booking** from this quote:
- ✅ The 5 Air freight charges are copied
- ❌ The 3 Customs charges are **NOT** copied
- ❌ The 2 Warehousing charges are **NOT** copied

## Why This Happens

The system is designed to only copy charges that match the booking type:
- **Air Booking** only copies charges marked as "Air" service type
- **Sea Booking** only copies charges marked as "Sea" service type  
- **Transport Order** only copies charges marked as "Transport" service type

This means any other charges (Customs, Warehousing, etc.) are left behind.

## Impact on Your Work

1. **Missing Charges**: You have to manually add Customs, Warehousing, and other charges after creating the booking/order
2. **Extra Work**: More time spent copying charges manually
3. **Risk of Errors**: Easy to forget to add charges, leading to incorrect pricing
4. **Incomplete Data**: The booking/order doesn't show the full picture from the Sales Quote

## The Fix Needed

The charge copying process needs to be updated to:
- Copy **ALL charges** from the Sales Quote, regardless of service type
- OR provide an option to choose which charges to copy

This would ensure that when you create a booking or order from a Sales Quote, you get all the charges automatically, saving time and reducing errors.
