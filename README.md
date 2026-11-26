# MTG price checker (first version)

**Status:** the site, matching and calculations work on made-up data. Not yet tested against the
live Card Kingdom list. There is NO automatic The TCG Marketplace collector yet; it depends on the
results of the probe test. Until then, listings come from `data/listings.csv`. Singles only.

## Publish
1. Upload these files to a repository. GitHub's upload page may miss the hidden `.github` folder:
   if so, create `.github/workflows/build-site.yml` with "Add file > Create new file".
2. Settings > Pages > Source: **GitHub Actions**. (Free accounts need a public repository for Pages.)
3. Actions > Build price site > Run workflow. Leave demo ticked first.
4. For real prices, add rows to `data/listings.csv`, then run with demo unticked.

A published site (and a public repository's CSV) can be seen by others. Check the marketplace's
terms before publishing its prices. There is no schedule yet: add one once collection works.

## listings.csv
| column | notes |
|---|---|
| name, set_name, variation | Must match Card Kingdom's wording unless an ID is given |
| finish | nonfoil, foil, or a listed special finish such as `etched` or `surge foil` |
| condition | NM, EX, VG or G (Card Kingdom's scale). Don't assume another site's grades are equal |
| language | English |
| price_sgd, quantity | Price per card |
| url, checked_at | Optional listing link (https) and when you saw the price |
| scryfall_id, ck_sku | Optional; the most reliable way to match a version |

Skipped rows and reasons are written to `skipped.json` on the site. Blank finishes, unknown finishes
and matches with more than one possible version are skipped. Special finishes are recognised from
Card Kingdom's variation/set wording using the `SPECIAL` list in `build.py`; that wording is
unverified against live data, so check foil matches by hand on your first real run.

## Calculations
- Selling-price change = CK selling price (same condition) x rate - your price - extra cost
- Buylist change = CK buylist x 1.15 x rate - your price - extra cost (NM only, and only if CK is buying)
- Percentage = change / (your price + extra cost)

## Run on your computer
    python build.py --demo
    python -m http.server -d site 8000
