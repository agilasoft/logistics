# v1.0-fix: additional features, bug fix

**Base:** `v1.0-stable` ← **Compare:** `develop`  
**Deploy target:** atndemo

## Summary

Deploy latest Exhibits enhancements and fixes to **atndemo** (4 commits ahead of `v1.0-stable`).

## What's included

### Exhibits — new features

- **Internal Jobs tab** on Exhibit with `Internal Job Detail` child rows
- **Create Booking / Order** from Exhibit — spawn Air/Sea bookings, Transport orders, Declarations, and Inbound orders from internal job rows
- **Charge allocation** — allocate exhibit consolidation charges to **Dockets** or **Exhibit Jobs** (Equal or Custom % basis; Auto target selection)
- New child doctypes: **Exhibit Consolidation Charges**, **Exhibit Cost Allocation**

### Bug fixes

- Fix Exhibit **save error** on the dockets field
- Register **activity code seed patch** (`v1_0_seed_exhibit_activity_codes`) so migrate seeds Activity Code rows on existing sites (prevents lifecycle job save failures)

## Migration

- Run `bench migrate` after deploy — required for the activity code seed patch and new Exhibit doctype fields/tables

## Test plan

- [ ] Open an existing Exhibit — confirm it saves without errors
- [ ] Add internal jobs on the Jobs tab and use **Create > Booking / Order**
- [ ] Add consolidation charges and run **Allocate Costs** (Equal and Custom %)
- [ ] Verify allocated amounts roll up on Dockets / Exhibit Jobs as expected
- [ ] Smoke-test Air/Sea booking and Transport order creation from an Exhibit

## Short version (for PR description field)

- Exhibits: Internal Jobs tab + Create Booking/Order from Exhibit
- Exhibits: Charge allocation to Dockets and Exhibit Jobs
- Fix: Exhibit save error on dockets field
- Fix: Activity Code seed patch registered for migrate
- **Deploy target:** atndemo — run `bench migrate` after update
