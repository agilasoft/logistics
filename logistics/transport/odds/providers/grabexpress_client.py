# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
GrabExpress API Client

Implements GrabExpress on-demand delivery API per:
https://developer-beta.stg-myteksi.com/docs/grab-express/#grabexpress

- OAuth2 client_credentials authentication
- Get Delivery Quotes (POST /v1/deliveries/quotes)
- Create Delivery Request (POST /v1/deliveries)
- Get Delivery Details (GET /v1/deliveries/{deliveryID})
- Cancel Delivery (DELETE /v1/deliveries/{deliveryID})
"""

import frappe
import requests
import json
import time
from typing import Dict, Any, Optional
from ..base import ODDSClient
from ..exceptions import (
    ODDSAPIException,
    ODDSAuthenticationException,
)


class GrabExpressClient(ODDSClient):
    """
    GrabExpress API Client

    Uses OAuth2 client_credentials for authentication.
    Staging: https://partner-api.grab.com/grab-express-sandbox
    Production: https://partner-api.grab.com/grab-express
    """

    TOKEN_URL = "https://partner-api.grab.com/grabid/v1/oauth2/token"
    OAUTH_SCOPE = "grab_express.partner_deliveries"

    def __init__(self, settings: Dict[str, Any]):
        super().__init__("grabexpress", settings)

        self.client_id = settings.get("api_key") or settings.get("client_id")
        self.client_secret = settings.get("api_secret") or settings.get("client_secret")
        self.environment = settings.get("environment", "sandbox").lower()

        if self.environment == "production":
            self.base_url = "https://partner-api.grab.com/grab-express"
        else:
            self.base_url = "https://partner-api.grab.com/grab-express-sandbox"

        if not self.client_id or not self.client_secret:
            raise ODDSAuthenticationException(
                "GrabExpress OAuth credentials (client_id/client_secret) not configured",
                provider="grabexpress"
            )

        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """Obtain or refresh OAuth2 access token"""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token

        try:
            response = requests.post(
                self.TOKEN_URL,
                headers={
                    "Cache-Control": "no-cache",
                    "Content-Type": "application/json",
                },
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                    "scope": self.OAUTH_SCOPE,
                },
                timeout=15,
            )

            if not response.ok:
                frappe.log_error(
                    f"GrabExpress OAuth failed: {response.status_code} {response.text}",
                    "GrabExpress OAuth Error"
                )
                raise ODDSAuthenticationException(
                    f"OAuth token request failed: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json() if response.text else {},
                    provider="grabexpress"
                )

            data = response.json()
            self._access_token = data.get("access_token")
            expires_in = int(data.get("expires_in", 604799))  # 7 days default
            self._token_expires_at = time.time() + expires_in

            return self._access_token

        except requests.exceptions.RequestException as e:
            frappe.log_error(f"GrabExpress OAuth request failed: {str(e)}", "GrabExpress OAuth Error")
            raise ODDSAuthenticationException(
                f"OAuth request failed: {str(e)}",
                provider="grabexpress"
            )

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with Bearer token"""
        token = self._get_access_token()
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Cache-Control": "no-cache",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to GrabExpress API"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ODDSAPIException(f"Unsupported method: {method}", provider="grabexpress")

            if response.status_code == 401:
                self._access_token = None
                return self._make_request(method, endpoint, data, params)

            if not response.ok:
                try:
                    err_data = response.json()
                except Exception:
                    err_data = {"raw": response.text}
                error_msg = err_data.get("message", err_data.get("error", response.text))
                raise ODDSAPIException(
                    f"GrabExpress API error: {error_msg}",
                    status_code=response.status_code,
                    response_data=err_data,
                    provider="grabexpress"
                )

            if response.status_code == 204:
                return {"success": True}

            return response.json()

        except requests.exceptions.RequestException as e:
            frappe.log_error(f"GrabExpress API request failed: {str(e)}", "GrabExpress API Error")
            raise ODDSAPIException(f"Request failed: {str(e)}", provider="grabexpress")

    def get_quotation(self, quotation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get delivery quotes (POST /v1/deliveries/quotes)

        Request must include: packages, origin, destination
        Optional: serviceType, vehicleType, codType, promoCode
        """
        return self._make_request("POST", "/v1/deliveries/quotes", data=quotation_request)

    def get_quotation_details(self, quotation_id: str) -> Dict[str, Any]:
        """
        GrabExpress does not have a separate quotation details endpoint.
        Returns cached/minimal data. Use get_quotation for fresh quotes.
        """
        return {
            "quotation_id": quotation_id,
            "message": "GrabExpress quotes are obtained via get_quotation; use that for fresh pricing",
        }

    def place_order(self, quotation_id: str, order_request: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create delivery (POST /v1/deliveries)

        order_request must include: merchantOrderID, serviceType, packages, origin,
        destination, sender, recipient. Optional: schedule, paymentMethod, codType.
        """
        if not order_request:
            raise ODDSAPIException(
                "GrabExpress requires full order request (sender, recipient, etc.)",
                provider="grabexpress"
            )
        return self._make_request("POST", "/v1/deliveries", data=order_request)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Get delivery details (GET /v1/deliveries/{deliveryID})"""
        return self._make_request("GET", f"/v1/deliveries/{order_id}")

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel delivery (DELETE /v1/deliveries/{deliveryID})"""
        return self._make_request("DELETE", f"/v1/deliveries/{order_id}")

    def get_driver_details(self, driver_id: str) -> Dict[str, Any]:
        """
        GrabExpress returns driver info in get_order_details (courier object).
        No separate driver endpoint.
        """
        return {"driver_id": driver_id, "message": "Use get_order_details for courier info"}
