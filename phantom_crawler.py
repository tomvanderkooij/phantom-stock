#!/usr/bin/env python3
"""
Phantom Athletics stock crawler.

Haalt alle producten op van https://phantom-athletics.com/products.json
en schrijft een CSV in het formaat dat door Stock Sync (Shopify) gelezen
kan worden:

    SKU,Quantity,Price

Quantity = "in_stock" of "out_of_stock" (gebaseerd op Shopify's
`available` veld op variant-niveau). De publieke Shopify endpoint geeft
geen exacte voorraadaantallen terug — alleen of de variant te koop is.

Gebruik:
    python3 phantom_crawler.py [output_path.csv]

Standaard schrijft het script naar `phantom_stock.csv` in dezelfde map.
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_URL = "https://phantom-athletics.com/products.json"
PAGE_SIZE = 250          # Shopify maximum
MAX_PAGES = 50           # safety cap (12.500 producten)
RETRIES = 3
RETRY_SLEEP = 3          # seconden tussen retries
USER_AGENT = "PhantomStockCrawler/1.0 (+stocksync)"


def fetch_page(page: int) -> list[dict]:
    """Haal één pagina van Shopify op met retries."""
    url = f"{BASE_URL}?limit={PAGE_SIZE}&page={page}"
    last_err: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read())
            return payload.get("products", [])
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(RETRY_SLEEP * attempt)
    raise RuntimeError(f"Kon pagina {page} niet ophalen: {last_err}")


def crawl_all() -> list[dict]:
    """Loop door alle pagina's totdat een lege pagina terugkomt."""
    products: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        batch = fetch_page(page)
        if not batch:
            break
        products.extend(batch)
        # Wees vriendelijk voor de server
        time.sleep(0.4)
    return products


def to_rows(products: list[dict]) -> list[dict]:
    """Lijst van varianten met SKU, Quantity, Price.

    Phantom listet sommige varianten onder meerdere productpagina's met
    dezelfde SKU. Voor Stock Sync moet elke SKU uniek zijn, dus we
    dedupliceren: bij dubbele SKU's wint `in_stock` (als minstens één
    listing voorraad heeft) en behouden we de eerste titel/prijs/url.
    """
    by_sku: dict[str, dict] = {}
    duplicates_seen = 0
    for product in products:
        title = product.get("title", "")
        handle = product.get("handle", "")
        product_url = f"https://phantom-athletics.com/products/{handle}"
        for variant in product.get("variants", []):
            sku = (variant.get("sku") or "").strip()
            if not sku:
                # Producten zonder SKU slaan we over — niet te matchen
                # tegen onze eigen Shopify catalog.
                continue
            available = bool(variant.get("available"))
            existing = by_sku.get(sku)
            if existing is None:
                by_sku[sku] = {
                    "SKU": sku,
                    "Quantity": "in_stock" if available else "out_of_stock",
                    "Price": variant.get("price", ""),
                    "Title": title,
                    "Variant": variant.get("title", ""),
                    "ProductURL": product_url,
                }
            else:
                duplicates_seen += 1
                # Eén keer "in_stock" is genoeg om de SKU als beschikbaar
                # te markeren.
                if available and existing["Quantity"] != "in_stock":
                    existing["Quantity"] = "in_stock"
    if duplicates_seen:
        print(f"  Dubbele SKU listings samengevoegd: {duplicates_seen}")
    return list(by_sku.values())


def write_csv(rows: list[dict], path: Path) -> None:
    # Stock Sync verwacht puur SKU,Quantity,Price. We schrijven die drie
    # kolommen eerst en plakken de overige info erachter — niet-gebruikte
    # kolommen kunnen in Stock Sync genegeerd worden.
    fieldnames = ["SKU", "Quantity", "Price", "Title", "Variant", "ProductURL"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("phantom_stock.csv")
    started = datetime.now()
    print(f"[{started:%Y-%m-%d %H:%M:%S}] Start crawl van {BASE_URL}")
    products = crawl_all()
    rows = to_rows(products)
    write_csv(rows, out_path)
    in_stock = sum(1 for r in rows if r["Quantity"] == "in_stock")
    finished = datetime.now()
    print(f"[{finished:%Y-%m-%d %H:%M:%S}] Klaar in {(finished - started).seconds}s")
    print(f"  Producten      : {len(products)}")
    print(f"  SKUs (varianten): {len(rows)}")
    print(f"  In stock       : {in_stock}")
    print(f"  Out of stock   : {len(rows) - in_stock}")
    print(f"  CSV            : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
