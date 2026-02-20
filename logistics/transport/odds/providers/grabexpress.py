# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
GrabExpress Provider Implementation

ODDS provider for GrabExpress on-demand delivery service.
API reference: https://developer-beta.stg-myteksi.com/docs/grab-express/#grabexpress
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from .grabexpress_client import GrabExpressClient
from .grabexpress_mapper import GrabExpressMapper


class GrabExpressProvider(ODDSProvider):
    """GrabExpress provider implementation"""

    @property
    def provider_name(self) -> str:
        return "GrabExpress"

    @property
    def provider_code(self) -> str:
        return "grabexpress"

    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get GrabExpress API client"""
        if settings is None:
            settings = self._get_settings()
        return GrabExpressClient(settings)

    def get_mapper(self) -> ODDSMapper:
        """Get GrabExpress mapper"""
        return GrabExpressMapper()

    def get_settings_doctype(self) -> str:
        return "ODDS Settings"

    def _get_settings(self) -> Dict[str, Any]:
        """Get GrabExpress settings from ODDS Settings"""
        try:
            from frappe.utils.password import get_decrypted_password

            settings = frappe.get_single("ODDS Settings")
            if not getattr(settings, "grabexpress_enabled", False):
                raise Exception("GrabExpress integration is not enabled")

            api_secret = get_decrypted_password(
                "ODDS Settings",
                "ODDS Settings",
                "grabexpress_api_secret",
                raise_exception=False,
            )
            return {
                "api_key": settings.grabexpress_api_key,
                "api_secret": api_secret,
                "environment": getattr(settings, "grabexpress_environment", "sandbox") or "sandbox",
            }
        except Exception as e:
            frappe.log_error(f"Error getting GrabExpress settings: {str(e)}", "GrabExpress Settings Error")
            raise
