# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
GrabExpress Provider Implementation

ODDS provider for GrabExpress on-demand delivery service.
"""

import frappe
from typing import Dict, Any
from ..base import ODDSProvider, ODDSClient, ODDSMapper
from ..exceptions import ODDSProviderNotSupportedException


class GrabExpressProvider(ODDSProvider):
    """GrabExpress provider implementation (stub)"""
    
    @property
    def provider_name(self) -> str:
        return "GrabExpress"
    
    @property
    def provider_code(self) -> str:
        return "grabexpress"
    
    def get_client(self, settings: Dict[str, Any] = None) -> ODDSClient:
        """Get GrabExpress API client"""
        # TODO: Implement GrabExpress client
        raise ODDSProviderNotSupportedException("GrabExpress provider not yet implemented")
    
    def get_mapper(self) -> ODDSMapper:
        """Get GrabExpress mapper"""
        # TODO: Implement GrabExpress mapper
        raise ODDSProviderNotSupportedException("GrabExpress provider not yet implemented")
    
    def get_settings_doctype(self) -> str:
        return "ODDS Settings"

