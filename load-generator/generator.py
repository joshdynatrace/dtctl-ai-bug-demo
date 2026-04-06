#!/usr/bin/env python3
"""
Arc Store load generator.
Continuously places random orders against the backend, reproducing the
tax-service NPE on products with an unregistered tax code (e.g. Arc Display).
"""

import os
import time
import random
import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
PRODUCTS_URL = f"{BACKEND_URL}/api/products"
ORDERS_URL   = f"{BACKEND_URL}/api/orders"
DELAY        = float(os.getenv("DELAY_SECONDS", "5"))

STATES = ["CA", "NY", "TX"]


def get_products():
    try:
        resp = requests.get(PRODUCTS_URL, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[WARN]  Could not fetch products: {exc}")
        return []


def place_order(product_id, product_name, quantity, shipping_state):
    try:
        resp = requests.post(
            ORDERS_URL,
            json={"productId": product_id, "quantity": quantity, "shippingState": shipping_state},
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


def wait_for_backend():
    print(f"Waiting for backend at {BACKEND_URL} ...")
    while True:
        products = get_products()
        if products:
            names = ", ".join(p["name"] for p in products)
            print(f"Backend ready. Products: {names}")
            return products
        time.sleep(2)


def main():
    print("Arc Store load generator starting")
    products = wait_for_backend()

    while True:
        products = get_products() or products

        product       = random.choice(products)
        quantity      = random.randint(1, 3)
        shipping_state = random.choice(STATES)
        place_order(product["id"], product["name"], quantity, shipping_state)
        time.sleep(DELAY)


if __name__ == "__main__":
    main()
