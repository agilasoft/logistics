# Separate Billings per Service Type

## In one sentence

The **Separate Billings per Service Type** checkbox on the Sales Quote controls whether the customer is billed from **one document** (e.g. the main Air Booking) or from **each service document** (Air, Sea, Customs, etc.) separately.

---

## Unchecked = one bill

**Use when:** You want a single document to bill the customer.

- The **Main Job** (e.g. Air Booking) receives **all** charges from the quote — Air, Customs, Warehousing, and any others.
- Other jobs (Customs, Warehousing, etc.) are still created for operations and tracking, but they do not bill the customer on their own.
- If a service has no charges in the quote, that job is created as an **Internal Job** (no separate billing).

**Example:** Quote has 5 Air + 3 Customs + 2 Warehousing charges, and the main job is the Air Booking.  
→ The Air Booking gets all 10 charges. Customs and Warehousing exist for operations but do not carry the full billing.

---

## Checked = each service bills separately

**Use when:** You want each service to invoice the customer on its own.

- Each document gets **only** its own charges: Air Booking → Air only, Declaration → Customs only, and so on.
- If a service has no charges in the quote, that job is an **Internal Job**.

**Example:** Same quote (5 Air + 3 Customs + 2 Warehousing).  
→ Air Booking gets 5 charges, Customs gets 3, Warehousing gets 2. Each can bill the customer separately.

---

## What is an Internal Job?

An **Internal Job** is a Booking/Order used for **tracking and operations only**, with no separate customer invoice for that service.

- The customer is billed from the Main Job (or another document).
- Example: Customs work is done and tracked, but the amount is included in the Air freight and billed from the Air Booking.

---

## Quick choice

| Goal | Checkbox |
|------|----------|
| One document bills the customer | **Unchecked** |
| Each service bills the customer separately | **Checked** |

---

## How to use it

1. Set the checkbox on the Sales Quote and **save**.
2. Add your charges on the Sales Quote and **save** again.
3. Create Bookings/Orders from the quote (e.g. from the **Connections** tab). Use “Create Air Booking”, “Create Sea Booking”, etc.

Charges are copied from the quote into the new booking or order. If you have unsaved changes when you click “Create Air Booking” (or Sea Booking), the system will save the Sales Quote first so that all charges are included.
