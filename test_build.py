import unittest, build

class T(unittest.TestCase):
    def setUp(self):
        self.ck, self.rows = build.demo()
        self.deals, self.skipped = build.build(self.ck, self.rows)

    def test_cheapest_per_version(self):
        self.assertEqual(len(self.deals), 5)
        self.assertEqual([d["buy_sgd"] for d in self.deals if d["name"] == "Sample Dragon" and not d["foil"]], [8.0])

    def test_special_foil_never_matches_plain_foil(self):
        row = dict(self.rows[3], variation="")
        row["finish"] = "foil"; row["variation"] = "Borderless - Surge Foil"
        self.assertEqual(build.build(self.ck, [row])[0], [])

    def test_shared_scryfall_id(self):
        base = dict(self.ck["data"][1], scryfall_id="abc")
        other = dict(base, id=99, variation="Surge Foil")
        idx = build.Index([base, other])
        self.assertEqual(idx.match({"finish": "foil", "scryfall_id": "abc"})[0]["id"], 2)
        self.assertEqual(idx.match({"finish": "surge foil", "scryfall_id": "abc"})[0]["id"], 99)
        self.assertIsNone(idx.match({"finish": "etched", "scryfall_id": "abc"})[0])
        dup = build.Index([base, dict(base, id=100, variation="Showcase")])
        self.assertEqual(dup.match({"finish": "foil", "scryfall_id": "abc"})[1], "more than one version fits")

    def test_not_buying(self):
        self.assertIsNone(next(d for d in self.deals if d["name"] == "Example Wizard")["ck_buylist_usd"])

    def test_bad_rows_skipped(self):
        r = self.rows[0]
        bad = [dict(r, language="Japanese"), dict(r, quantity=0), dict(r, price_sgd="nan"),
               dict(r, finish=""), dict(r, condition="LP"), dict(r, finish="sparkly")]
        deals, skipped = build.build(self.ck, bad)
        self.assertEqual((len(deals), len(skipped)), (0, 6))

    def test_non_nm_has_no_buylist(self):
        self.ck["data"][0]["condition_values"]["ex_price"] = "10.00"
        d = build.build(self.ck, [dict(self.rows[0], condition="EX")])[0][0]
        self.assertEqual((d["ck_retail_usd"], d["ck_buylist_usd"]), (10.0, None))

if __name__ == "__main__":
    unittest.main()
