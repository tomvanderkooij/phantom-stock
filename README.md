# Phantom Athletics stock feed

Crawlt elke 12 uur automatisch de volledige Phantom Athletics catalog
(`https://phantom-athletics.com`) en publiceert het resultaat als CSV op
een vaste URL. Bedoeld om als bronfeed te gebruiken in Stock Sync (of
een vergelijkbare Shopify stock-import app).

Het idee is hetzelfde als het bestand dat Venum aanlevert
(`product_venum_stock.csv`): één URL die jouw stock-app op een
ingestelde frequentie ophaalt.

## Wat erin zit

| Bestand | Functie |
|---|---|
| `phantom_crawler.py` | Python script dat alle producten van Phantom's publieke Shopify endpoint ophaalt en `phantom_stock.csv` genereert |
| `.github/workflows/crawl.yml` | GitHub Actions workflow die het script elke 12 uur draait en de CSV terug commit |
| `phantom_stock.csv` | Output. Wordt automatisch ververst door de workflow |
| `README.md` | Dit bestand |

## CSV formaat

```
SKU,Quantity,Price,Title,Variant,ProductURL
PHSH3867-S,out_of_stock,39.99,Heavy Tee Mexico,Small,https://phantom-athletics.com/products/heavy-tee-mexico
PHSH3867-M,in_stock,39.99,Heavy Tee Mexico,Medium,https://phantom-athletics.com/products/heavy-tee-mexico
...
```

- `SKU` — Phantom's SKU, uniek per regel (dubbele listings worden samengevoegd)
- `Quantity` — `in_stock` of `out_of_stock` (Phantom geeft geen exacte aantallen op het publieke kanaal)
- `Price` — adviesprijs in EUR
- `Title`, `Variant`, `ProductURL` — extra context voor handmatige controle; niet verplicht voor Stock Sync

## Setup (eenmalig, ~5 minuten)

1. **Maak een nieuwe GitHub repo** aan op <https://github.com/new>.
   - Naam bijvoorbeeld `phantom-stock`
   - Zichtbaarheid: **Public** (zodat de raw CSV-URL zonder token werkt)
   - Initialiseer met een README is niet nodig — we vullen alles zelf
2. **Upload de drie bestanden** in deze map naar de root van het repo
   (drag-and-drop op de GitHub UI werkt prima). Behoud de structuur:
   ```
   phantom_crawler.py
   phantom_stock.csv
   README.md
   .github/workflows/crawl.yml
   ```
3. **Geef Actions permissie om te committen**: Repo → *Settings* → *Actions* → *General* → onderaan *"Workflow permissions"* → kies **"Read and write permissions"** → *Save*.
4. **Test handmatig**: Repo → *Actions* tab → kies *"Crawl Phantom Athletics stock"* → *"Run workflow"*. Na ±30s zie je een groene check en is `phantom_stock.csv` ververst.
5. **Stock Sync URL**:
   ```
   https://raw.githubusercontent.com/<JOUW-USER>/<REPO>/main/phantom_stock.csv
   ```
   Plak deze in Stock Sync als bron-feed. Bijvoorbeeld:
   ```
   https://raw.githubusercontent.com/tomvdk/phantom-stock/main/phantom_stock.csv
   ```

Vanaf dat moment draait alles automatisch. Stock Sync haalt de URL op
volgens jouw eigen sync-interval; GitHub Actions ververst de CSV om
06:00 en 18:00 UTC (08:00 / 20:00 in NL).

## Frequentie aanpassen

In `.github/workflows/crawl.yml` staat:

```yaml
schedule:
  - cron: "0 6,18 * * *"   # UTC!
```

Voorbeelden:
- `"0 */6 * * *"` — elke 6 uur
- `"0 6 * * *"`  — eens per dag (08:00 NL)
- `"*/30 * * * *"` — elke 30 minuten (overdrijf niet, GitHub heeft soft caps)

Onthoud dat GitHub Actions cron in **UTC** werkt — geen lokale tijd.

## Privé repo (alternatief)

Als je het repo liever privé houdt, vereist de raw URL een Personal
Access Token. In Stock Sync kun je dan een custom header toevoegen:

```
Authorization: token ghp_xxxxxxxxxxxxxxxxxxxx
```

Maak de token aan onder Settings → Developer settings → Personal access
tokens → "Fine-grained" met alleen *Contents: Read* op dit ene repo.

## Lokaal draaien (debug)

```bash
python3 phantom_crawler.py phantom_stock.csv
```

Voorbeeldoutput:

```
[2026-05-01 09:37:12] Start crawl
  Dubbele SKU listings samengevoegd: 6078
[2026-05-01 09:37:25] Klaar in 12s
  Producten: 1261 | SKUs: 5174 | in_stock: 3091 | out: 2083
  CSV: phantom_stock.csv
```

## Bekende beperkingen

- **Geen exacte voorraad**. Phantom verbergt `inventory_quantity` op het
  publieke Shopify endpoint — alleen in/out is beschikbaar. Voor exacte
  aantallen moet je het B2B portaal of de Shopify Admin API gebruiken
  (vereist credentials van Phantom).
- **Dubbele listings**. ~1.300 SKU's komen meerdere keren voor in
  Phantom's catalog (zelfde hoodie, twee productpagina's). Het script
  dedupliceert: één regel per SKU, en als minstens één listing in stock
  is wint dat.
- **Cron drift**. GitHub kan een cron job tot enkele minuten
  vertragen onder hoge load. Voor stock-sync is dat geen probleem.
