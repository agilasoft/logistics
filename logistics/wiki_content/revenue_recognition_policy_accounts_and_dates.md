# Revenue Recognition Policy — Accounts, Dates, and Charges

## Overview

**Revenue Recognition Policy Settings** (DocType: *Recognition Policy Settings*) is **one document per company**. Rules are defined in the **Recognition Parameters** child table (match by Branch, Profit Center, Cost Center, Direction, Transport Mode).

## Recognition date

- There is a **single Recognition Date Basis** per parameter row (not separate WIP vs accrual).
- **WIP** and **cost accrual** journal entries use the **same posting date**, derived from that basis.
- On jobs/shipments/declarations, **Revenue & Cost Recognition** shows:
  - **Recognition Date Basis** (read-only, from policy)
  - **Recognition Date** (posting date): read-only except when the basis is **User Specified**, in which case the user enters the date on the job.

Basis options: ATA, ATD, Job Booking Date, Job Creation, User Specified.

## GL accounts (parameter row)

| Field | Account filter | Job Profit Account Type |
|-------|----------------|-------------------------|
| **WIP Account** | Income Account | **WIP** (required) |
| **Revenue Liability Account** | Asset (root type) | *(not restricted)* |
| **Cost Accrual Account** | Expense Account | **Accrual** (required) |
| **Accrued Cost Liability Account** | Liability | *(not restricted)* |

### WIP recognition entry (conceptual)

- **Dr** Revenue Liability Account (Asset — WIP / unbilled position per chart of accounts)  
- **Cr** WIP Account (Income, WIP)

### Accrual recognition entry (unchanged)

- **Dr** Cost Accrual Account (Expense, Accrual)  
- **Cr** Accrued Cost Liability Account (Liability)

## Disbursement charges

Lines with **Charge Type = Disbursement** are **excluded** from:

- Estimated revenue used for WIP recognition  
- Estimated cost used for cost accrual recognition  

Profit, WIP, and Accrual recognition apply only to non-disbursement charge lines (e.g. Revenue / Cost charge types).

## Migration note

If you previously used different account types (e.g. Asset WIP), update **Recognition Parameters** to match the table above before saving the policy document; validation enforces these rules on each parameter row.
