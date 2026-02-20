# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
NinjaVAN Provider Implementation

ODDS provider for NinjaVAN on-demand delivery service.
API reference: https://api-docs.ninjavan.co/en
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from ..exceptions import ODDSProviderNotSupportedException


class NinjaVANProvider(ODDSProvider):
    """NinjaVAN provider implementation (stub)"""

    @property
    def provider_name(self) -> str:
        return "NinjaVAN"

    @property
    def provider_code(self) -> str:
        return "ninjavan"

    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get NinjaVAN API client. Implement per https://api-docs.ninjavan.co/en"""
        raise ODDSProviderNotSupportedException(
            "NinjaVAN provider not yet implemented. See https://api-docs.ninjavan.co/en"
        )

    def get_mapper(self) -> ODDSMapper:
        """Get NinjaVAN mapper. Implement per https://api-docs.ninjavan.co/en"""
        raise ODDSProviderNotSupportedException(
            "NinjaVAN provider not yet implemented. See https://api-docs.ninjavan.co/en"
        )

    def get_settings_doctype(self) -> str:
        return "ODDS Settings"

