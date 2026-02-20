# ODDS Provider API References

This document lists the official API documentation for On-Demand Delivery Service (ODDS) providers integrated with the logistics app.

## GrabExpress

**Status:** ✅ Implemented

**API Documentation:** https://developer-beta.stg-myteksi.com/docs/grab-express/#grabexpress

**Regions:** Indonesia, Malaysia, Philippines, Singapore, Thailand, Vietnam, Myanmar, Cambodia

**Key endpoints:**
- Get Delivery Quotes: `POST /v1/deliveries/quotes`
- Create Delivery: `POST /v1/deliveries`
- Get Delivery Details: `GET /v1/deliveries/{deliveryID}`
- Cancel Delivery: `DELETE /v1/deliveries/{deliveryID}`

**Authentication:** OAuth2 client_credentials (`client_id`, `client_secret`, scope: `grab_express.partner_deliveries`)

**ODDS Settings:** Use `grabexpress_api_key` as OAuth Client ID and `grabexpress_api_secret` as OAuth Client Secret.

---

## NinjaVAN

**Status:** 🔲 Stub (not yet implemented)

**API Documentation:** https://api-docs.ninjavan.co/en

**Implementation:** Provider stub exists at `logistics/transport/odds/providers/ninjavan.py`. Client and mapper need to be implemented per NinjaVAN API specification.

---

## Lalamove

**Status:** ✅ Implemented

**Implementation:** `lalamove_client_standalone.py`, `lalamove_mapper_standalone.py`

---

## Transportify (Deliveree)

**Status:** ✅ Implemented

**Implementation:** `transportify_client.py`, `transportify_mapper.py`

---

## PandaGo

**Status:** 🔲 Stub (not yet implemented)

**Implementation:** Provider stub exists at `logistics/transport/odds/providers/pandago.py`
