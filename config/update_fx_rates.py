"""Refresh config/fx_rates.json from the Riksbank's public SWEA API (mid rates, SEK per 1 unit).
Only currencies the Riksbank quotes per single unit are kept, so no per-100 scaling is needed."""
import json, urllib.request, pathlib
KEEP = ["EUR", "USD", "GBP", "NOK", "DKK", "CHF", "CAD", "AUD", "PLN", "CZK", "CNY", "NZD"]
data = json.load(urllib.request.urlopen("https://api.riksbank.se/swea/v1/Observations/Latest/ByGroup/130", timeout=20))
rates, as_of = {"SEK": 1.0}, None
for o in data:
    cur = o["seriesId"][3:6]
    if cur in KEEP and o["seriesId"].endswith("PMI"):
        rates[cur] = o["value"]; as_of = max(as_of or o["date"], o["date"])
out = {"source": "Sveriges Riksbank, mid rates (SWEA group 130)", "as_of": as_of, "sek_per_unit": rates}
pathlib.Path(__file__).with_name("fx_rates.json").write_text(json.dumps(out, indent=2) + "\n")
print(as_of, rates)
