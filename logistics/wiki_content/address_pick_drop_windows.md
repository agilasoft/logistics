# Address Pick / Drop Windows

Configure facility hours on **Address** using a single schedule table. There is no separate default window and no day-checkbox setup — the table is the only source of truth.

## Where to set it

1. Open an **Address**.
2. Open the **Transport** tab.
3. Use the **Pick / Drop Windows** table.

## How to set it up

1. Add one row per allowed **day** and **operation** (Pick or Drop).
2. Set **Start** and **End** for that row.
3. Optionally add **Remarks**.
4. **Save**.

| Day | Operation | Start | End | Remarks |
|-----|-----------|-------|-----|---------|
| Monday | Pick | 08:00 | 12:00 | |
| Monday | Drop | 13:00 | 17:00 | |
| Tuesday | Pick | 14:00 | 18:00 | Afternoon only |
| Tuesday | Drop | 14:00 | 18:00 | |

## Rules

- A row for that day + operation = **allowed**, with those times.
- No row for that day + operation = **not available**.
- Different days can have different windows.
- Each `(Day, Operation)` pair may appear only once.
- End must be after Start.

## Expected behaviour

| Situation | Behaviour |
|-----------|-----------|
| Matching schedule row | That start–end is used as the window |
| No matching row | Operation not allowed that weekday |
| Empty table | No day/operation allowed via Address schedule (when constraints are on) |
| Transport Leg with address + date | Pick/Drop windows fill from the matching weekday row |
| Address set, no leg date yet | Windows stay blank until a date exists |
| User edits leg windows manually | Kept for that leg if address/date do not change |
| Transport Plan assignment | Uses the schedule for day availability and time windows when those constraints are enabled in [Transport Settings](welcome/transport-settings) |

## Related

- [Transport Leg](welcome/transport-leg) — windows may be filled from this schedule for the leg’s weekday
- [Transport Settings](welcome/transport-settings) — `Enable Address Day Availability` and `Enable Time Window Constraints`
