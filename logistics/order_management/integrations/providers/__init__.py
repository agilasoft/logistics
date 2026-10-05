# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from logistics.order_management.integrations.providers.facebook import FacebookAdapter
from logistics.order_management.integrations.providers.lazada import LazadaAdapter
from logistics.order_management.integrations.providers.pancake import PancakeAdapter
from logistics.order_management.integrations.providers.shopee import ShopeeAdapter
from logistics.order_management.integrations.providers.shopify import ShopifyAdapter
from logistics.order_management.integrations.providers.tiktok import TikTokAdapter
from logistics.order_management.integrations.providers.woocommerce import WooCommerceAdapter

__all__ = [
	"FacebookAdapter",
	"LazadaAdapter",
	"PancakeAdapter",
	"ShopeeAdapter",
	"ShopifyAdapter",
	"TikTokAdapter",
	"WooCommerceAdapter",
]
