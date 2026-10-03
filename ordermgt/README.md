# Order Management (`ordermgt`)

Separate Frappe app that pulls marketplace orders into CargoNext warehouse Release Orders (returns into Inbound Orders) and pushes Warehouse Items and available stock back to each shop.

Depends on ERPNext and the `logistics` app. It does not add a module inside logistics.

## Platforms

Shopee, Lazada, TikTok Shop, Pancake, Facebook catalog inventory, WooCommerce, and Shopify.

Pancake is the path for Facebook, Instagram, and Zalo inbox orders. A Pancake order whose origin already has a direct Sales Channel for the same customer is skipped.

## Install

```bash
cd ~/frappe-bench/apps
ln -sfn /path/to/logistics/ordermgt ordermgt
cd ordermgt && pip install -e .
cd ~/frappe-bench
bench --site <site> install-app ordermgt
bench --site <site> migrate
bench build --app ordermgt
```

## Desk

Workspace **Order Management**. Open a Sales Channel and use Sync Orders, Sync Items, or Push Stock.

Webhook:

`/api/method/ordermgt.order_management.webhook.handle?platform=<slug>&channel=<Sales Channel name>`
