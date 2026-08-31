#!/usr/bin/env python3
"""
Parser for the Gazpromneft station map (gpnbonus.ru/fuel/refuel-map).

Collects the G-95 status — in stock / out of stock / in transit — for every
station in the Sverdlovsk region (by default). The result goes to
data/stations.json, which the SPA (index.html) reads.

Standard library only. Requests are deliberately gentle on the source:
single-threaded, paused between calls, retried on transient failures.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://gpnbonus.ru"
LIST_URL = f"{BASE}/api/stations/list"
STATION_URL = f"{BASE}/api/stations/{{gpn_id}}"

SVERDLOVSK_REGION_ID = 2612765
G95_ID = 421

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"{BASE}/fuel/refuel-map",
    "Origin": BASE,
}


def post_json(url, payload, retries=3, timeout=20):
    body = json.dumps(payload).encode()
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 or e.code >= 500:
                time.sleep(2 * attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(2 * attempt)
        except json.JSONDecodeError as e:
            last_err = e
            time.sleep(2 * attempt)
    raise RuntimeError(f"Request to {url} failed: {last_err}")


def rest_status(rest):
    """Reduce a `rest` block to one of: available / absent / in_transit / unknown."""
    if not rest or not rest.get("since"):
        return "unknown"
    if rest.get("avail"):
        return "available"
    # same logic as the site: not avail && delivery !== 'no' -> the truck "in transit" badge
    if rest.get("delivery") not in (None, "no"):
        return "in_transit"
    return "absent"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", type=int, default=SVERDLOVSK_REGION_ID, help="region_id (defaults to Sverdlovsk region)")
    ap.add_argument("--city", default=None, help="filter by city (e.g. 'Екатеринбург'); the whole region by default")
    ap.add_argument("--fuel", type=int, default=G95_ID, help="fuel id (421 = G-95)")
    ap.add_argument("--delay", type=float, default=0.5, help="pause between requests, seconds")
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "stations.json"))
    args = ap.parse_args()

    print("Loading station list...", file=sys.stderr)
    data = post_json(LIST_URL, {})
    products = {p["id"]: p for p in data["oilProducts"]}
    fuel = products.get(args.fuel, {"shortTitle": str(args.fuel), "title": ""})

    stations = [s for s in data["stations"] if s.get("region_id") == args.region]
    if args.city:
        stations = [s for s in stations if (s.get("city") or "").lower() == args.city.lower()]
    stations.sort(key=lambda s: ((s.get("city") or ""), (s.get("address") or "")))
    print(f"Stations selected: {len(stations)}", file=sys.stderr)

    result = []
    errors = 0
    for i, s in enumerate(stations, 1):
        gpn_id = s["GPNAZSID"]
        print(f"[{i}/{len(stations)}] {s.get('city')} — {s.get('address')} (id {gpn_id})", file=sys.stderr)
        oils, err = [], None
        try:
            detail = post_json(STATION_URL.format(gpn_id=gpn_id), {})
            oils = detail.get("data") or []
        except Exception as e:  # noqa: BLE001
            errors += 1
            err = str(e)
            print(f"    error: {e}", file=sys.stderr)

        target = next((o for o in oils if o.get("id") == args.fuel), None)
        rest = (target or {}).get("rest") or {}
        price = ((target or {}).get("price") or {}).get("price")

        # in /list the "oils" field is sometimes a dict, sometimes an empty list
        list_oils = s.get("oils") if isinstance(s.get("oils"), dict) else {}

        result.append({
            "id": s["id"],
            "gpnId": gpn_id,
            "name": (s.get("name") or "").strip(),
            "number": (s.get("PNPONumber") or "").strip(),
            "city": s.get("city"),
            "address": s.get("address"),
            "lat": float(s["latitude"]) if s.get("latitude") else None,
            "lon": float(s["longitude"]) if s.get("longitude") else None,
            "workMode": s.get("workMode"),
            "open": s.get("open"),
            "sellsFuel": str(args.fuel) in list_oils,  # whether the list endpoint claims the station carries it
            "fuel": {
                "id": args.fuel,
                "shortTitle": fuel.get("shortTitle"),
                "title": fuel.get("title"),
                "price": price,
                "priceSince": ((target or {}).get("price") or {}).get("since"),
                "status": rest_status(rest) if target else "not_sold",
                "avail": rest.get("avail"),
                "since": rest.get("since"),
                "delivery": rest.get("delivery"),
            },
            "allFuels": [
                {
                    "id": o.get("id"),
                    "shortTitle": (o.get("product") or {}).get("shortTitle"),
                    "price": (o.get("price") or {}).get("price"),
                    "priceSince": (o.get("price") or {}).get("since"),
                    "status": rest_status(o.get("rest")),
                    "since": (o.get("rest") or {}).get("since"),
                    "delivery": (o.get("rest") or {}).get("delivery"),
                }
                for o in oils
            ],
            "error": err,
        })
        time.sleep(args.delay)

    # diff against the previous snapshot: what changed for the tracked fuel
    changes = []
    prev_path = Path(args.out)
    if prev_path.exists():
        try:
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            prev_by_id = {s["id"]: s for s in prev.get("stations", [])}
            for r in result:
                old = prev_by_id.get(r["id"])
                if not old:
                    continue
                o_st, n_st = old["fuel"]["status"], r["fuel"]["status"]
                if o_st != n_st:
                    changes.append({
                        "id": r["id"], "number": r["number"], "city": r["city"],
                        "address": r["address"], "from": o_st, "to": n_st,
                        "delivery": r["fuel"]["delivery"],
                    })
        except Exception as e:  # noqa: BLE001
            print(f"could not diff against the previous snapshot: {e}", file=sys.stderr)

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "regionId": args.region,
        "city": args.city,
        "fuel": {"id": args.fuel, "shortTitle": fuel.get("shortTitle"), "title": fuel.get("title")},
        "total": len(result),
        "errors": errors,
        "changes": changes,
        "previousAt": (json.loads(Path(args.out).read_text(encoding="utf-8")).get("generatedAt")
                       if Path(args.out).exists() else None),
        "stations": result,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    c = Counter(r["fuel"]["status"] for r in result)
    print(f"\nDone: {args.out}\n{fuel.get('shortTitle')} statuses: {dict(c)}; errors: {errors}", file=sys.stderr)
    if changes:
        print(f"Changes since the previous run ({len(changes)}):", file=sys.stderr)
        for ch in changes:
            print(f"  {ch['city']}, {ch['address']} (№{ch['number']}): {ch['from']} -> {ch['to']}", file=sys.stderr)
    elif out["previousAt"]:
        print("No changes since the previous run.", file=sys.stderr)


if __name__ == "__main__":
    main()
