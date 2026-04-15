#!/usr/bin/env python3
"""
Arc Store load generator.
Continuously places orders against Arc Display
"""

import os
import time
import random
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
PRODUCTS_URL = f"{BACKEND_URL}/api/products"
ORDERS_URL   = f"{BACKEND_URL}/api/orders"
TAX_PREVIEW_URL = f"{ORDERS_URL}/tax-preview"
DELAY        = float(os.getenv("DELAY_SECONDS", "5"))

STATES = ["CA", "NY", "TX"]
TARGET_PRODUCT_NAME = os.getenv("TARGET_PRODUCT_NAME", "Arc Display")


def get_products():
    try:
        resp = requests.get(PRODUCTS_URL, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[WARN]  Could not fetch products: {exc}")
        return []


def place_order(product_id, product_name, quantity, shipping_state, total=None):
    try:
        payload = {
            "productId": product_id,
            "quantity": quantity,
            "shippingState": shipping_state,
        }
        if total is not None:
            payload["total"] = total

        resp = requests.post(
            ORDERS_URL,
            json=payload,
            timeout=5,
        )
        if resp.status_code == 200:
            print(f"[200 OK]  {product_name!r:22s}  qty={quantity}  state={shipping_state}")
        else:
            try:
                error = resp.json().get("error", resp.text)
            except Exception:
                error = resp.text
            print(f"[{resp.status_code} ERR] {product_name!r:22s}  qty={quantity}  state={shipping_state}  error={error!r}")
    except Exception as exc:
        print(f"[ERROR]  {product_name!r}  qty={quantity}  exception={exc}")


def preview_tax(product_id, product_name, quantity, shipping_state):
    try:
        resp = requests.get(
            TAX_PREVIEW_URL,
            params={
                "productId": product_id,
                "quantity": quantity,
                "shippingState": shipping_state,
            },
            timeout=5,
        )

        if resp.status_code == 200:
            payload = resp.json()
            return payload.get("total")

        print(f"[BUG]    {product_name!r:22s}  qty={quantity}  state={shipping_state}  tax-preview status={resp.status_code}")
        return None
    except Exception as exc:
        print(f"[ERROR]  tax-preview {product_name!r}  qty={quantity}  exception={exc}")
        return None


def wait_for_backend():
    print(f"Waiting for backend at {BACKEND_URL} ...")
    while True:
        products = get_products()
        if products:
            names = ", ".join(p["name"] for p in products)
            print(f"Backend ready. Products: {names}")
            return products
        time.sleep(2)


def get_target_product(products, target_name):
    for product in products:
        if product.get("name") == target_name:
            return product
    return None


def main():
    print("Arc Store load generator starting")
    products = wait_for_backend()

    while True:
        products = get_products() or products
        product = get_target_product(products, TARGET_PRODUCT_NAME)
        if not product:
            print(f"[WARN]  Target product {TARGET_PRODUCT_NAME!r} not found; waiting for product list refresh")
            time.sleep(DELAY)
            continue

        quantity = 1
        shipping_state = random.choice(STATES)

        total = preview_tax(product["id"], product["name"], quantity, shipping_state)
        if total is None:
            time.sleep(DELAY)
            continue
        place_order(product["id"], product["name"], quantity, shipping_state, total=total)

        time.sleep(DELAY)


if __name__ == "__main__":
    main()
