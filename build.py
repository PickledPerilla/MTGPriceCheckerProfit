"""Match supplier listings to Card Kingdom products and write site/deals.json.

  python build.py            real run: downloads Card Kingdom, reads data/listings.csv
  python build.py --demo     made-up cards and prices, no network
"""
import argparse, csv, datetime as dt, json, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).parent
CK_URL = "https://api.cardkingdom.com/api/v2/pricelist"
CONDITIONS = {"NM": "nm", "EX": "ex", "VG": "vg", "G": "g"}
# Foil treatments that must never be confused with ordinary foil. Add new ones here.
SPECIAL = ["etched", "surge", "galaxy", "textured", "gilded", "halo", "confetti",
           "ripple", "fracture", "raised", "step-and-compleat", "oil slick",
           "neon ink", "rainbow", "double rainbow", "serialized", "mana", "invisible ink",
           "silver scroll", "dazzle", "first place", "magnified", "singularity"]


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).split())


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def truthy(v):
    return v is True or str(v).strip().lower() == "true"


def treatments(*texts):
    hay = " " + " ".join(norm(t) for t in texts) + " "
    return {norm(w) for w in SPECIAL if f" {norm(w)} " in hay}


class Index:
    def __init__(self, products):
        self.sku, self.scry, self.name = {}, {}, {}
        for p in products:
            foil = truthy(p.get("is_foil"))
            if p.get("sku"):
                self.sku[p["sku"].upper()] = p
            if p.get("scryfall_id"):
                self.scry.setdefault((p["scryfall_id"].lower(), foil), []).append(p)
            self.name.setdefault((norm(p.get("name")), norm(p.get("edition")), foil), []).append(p)

    def match(self, row):
        """Return (product, None) or (None, reason). Never guesses between versions."""
        finish = norm(row.get("finish"))
        if not finish:
            return None, "finish is blank"
        foil = finish not in ("nonfoil", "non foil", "regular")
        wanted = treatments(finish)
        if foil and finish != "foil" and not wanted:
            return None, f"unknown finish '{finish}'"

        def same_treatment(p):
            return treatments(p.get("variation"), p.get("edition")) == wanted

        sku = (row.get("ck_sku") or "").strip().upper()
        sid = (row.get("scryfall_id") or "").strip().lower()
        if sku:
            p = self.sku.get(sku)
            if not p:
                return None, "ck_sku not found"
            if truthy(p.get("is_foil")) != foil or not same_treatment(p):
                return None, "ck_sku finish differs from listing finish"
            if norm(p.get("name")) != norm(row.get("name")):
                return None, "ck_sku name differs from listing name"
            return p, None
        if sid:
            found = [p for p in self.scry.get((sid, foil), []) if same_treatment(p)]
        else:
            found = [p for p in self.name.get((norm(row.get("name")), norm(row.get("set_name")), foil), [])
                     if same_treatment(p) and norm(p.get("variation")) == norm(row.get("variation"))]
        if len(found) == 1:
            return found[0], None
        return None, "no matching version" if not found else "more than one version fits"


def build(ck, rows):
    index = Index(ck["data"])
    base = (ck.get("meta") or {}).get("base_url") or "https://www.cardkingdom.com/"
    best, skipped = {}, []
    for line, row in enumerate(rows, start=2):
        def skip(reason):
            skipped.append({"line": line, "name": row.get("name", ""), "reason": reason})
        cond = (row.get("condition") or "").strip().upper()
        lang = norm(row.get("language"))
        price, qty = num(row.get("price_sgd")), num(row.get("quantity"))
        if cond not in CONDITIONS:
            skip("condition must be NM, EX, VG or G"); continue
        if lang not in ("en", "english"):
            skip("only listings marked English are compared"); continue
        if not (0 < price < float("inf")) or not qty >= 1:
            skip("missing price or out of stock"); continue
        p, why = index.match(row)
        if not p:
            skip(why); continue
        key = (p["id"], cond)
        if key in best and best[key]["buy_sgd"] <= price:
            continue
        cv = p.get("condition_values") or {}
        retail = num(cv.get(CONDITIONS[cond] + "_price"))
        if not retail and cond == "NM":
            retail = num(p.get("price_retail"))
        buying = int(num(p.get("qty_buying")))
        # The feed has one buylist price. It is only applied to NM copies.
        buylist = num(p.get("price_buy")) if cond == "NM" and buying > 0 else 0
        url = (row.get("url") or "").strip()
        best[key] = {
            "name": p.get("name"), "set": p.get("edition"), "variation": p.get("variation") or "",
            "finish": norm(row.get("finish")), "foil": truthy(p.get("is_foil")), "condition": cond,
            "scryfall_id": p.get("scryfall_id") or "", "buy_sgd": price, "quantity": int(qty),
            "supplier_url": url if url.startswith("https://") else "",
            "checked_at": (row.get("checked_at") or "").strip(),
            "ck_url": base.rstrip("/") + "/" + str(p.get("url", "")).lstrip("/"),
            "ck_retail_usd": retail or None,
            "ck_retail_qty": int(num(cv.get(CONDITIONS[cond] + "_qty"))),
            "ck_buylist_usd": buylist or None, "ck_buying_qty": buying,
        }
    return list(best.values()), skipped


def demo():
    def ck(i, name, edition, var, foil, retail, buy, want):
        return {"id": i, "sku": f"DEMO-{i}", "scryfall_id": "", "url": "", "name": name, "edition": edition,
                "variation": var, "is_foil": str(foil).lower(), "price_retail": str(retail),
                "price_buy": str(buy), "qty_buying": want,
                "condition_values": {"nm_price": str(retail), "nm_qty": 3}}
    products = [ck(1, "Sample Dragon", "Demo Set One", "", False, 12.0, 7.5, 4),
                ck(2, "Sample Dragon", "Demo Set One", "", True, 25.0, 14.0, 2),
                ck(3, "Sample Dragon", "Demo Set One", "Borderless - Surge Foil", True, 60.0, 38.0, 1),
                ck(4, "Example Wizard", "Demo Set Two", "Showcase", False, 4.0, 1.5, 0),
                ck(5, "Placeholder Relic", "Demo Set Two", "Foil Etched", True, 9.0, 5.0, 8)]
    rows = []
    for p, finish, price in [(products[0], "nonfoil", 8.0), (products[0], "nonfoil", 9.5),
                             (products[1], "foil", 30.0), (products[2], "surge foil", 45.0),
                             (products[3], "nonfoil", 6.0), (products[4], "etched", 5.5)]:
        rows.append({"name": p["name"], "set_name": p["edition"], "variation": p["variation"],
                     "finish": finish, "condition": "NM", "language": "English",
                     "price_sgd": price, "quantity": 1})
    return {"meta": {}, "data": products}, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        ck, rows = demo()
    else:
        with (ROOT / "data/listings.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            sys.exit("data/listings.csv has no listings. Add some, or run with --demo.")
        req = urllib.request.Request(CK_URL, headers={"User-Agent": "mtg-price-checker/0.1"})
        with urllib.request.urlopen(req, timeout=180) as r:
            ck = json.load(r)
    deals, skipped = build(ck, rows)
    if not deals:
        sys.exit(f"No listings matched; site not updated. First reasons: {skipped[:5]}")
    out = {"demo": args.demo, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "ck_created_at": (ck.get("meta") or {}).get("created_at", ""),
           "skipped_count": len(skipped), "deals": deals}
    (ROOT / "site/deals.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    (ROOT / "site/skipped.json").write_text(json.dumps(skipped, indent=1), encoding="utf-8")
    print(f"{len(deals)} versions written, {len(skipped)} listings skipped")


if __name__ == "__main__":
    main()
