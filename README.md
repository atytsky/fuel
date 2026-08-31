# G-95 fuel availability at Gazpromneft stations (Sverdlovsk region)

`parser.py` queries the public API behind the [Gazpromneft refuel map](https://gpnbonus.ru/fuel/refuel-map)
(`POST /api/stations/list` for the station list, `POST /api/stations/{GPNAZSID}` for prices and stock)
and writes a snapshot to `data/stations.json`. `index.html` is a build-free SPA that reads that JSON and
shows the G-95 status per station: **out of stock**, **🚚 in transit**, in stock, not sold.

Live page: **https://atytsky.github.io/fuel/**

Python 3 only, no dependencies.

## Usage

```sh
./update.sh                 # parse -> commit -> push (what the schedule runs)
python3 parser.py           # refresh data only (~2 min for 145 stations)
python3 parser.py --city Екатеринбург --delay 1   # single city, slower pace
./serve.sh                  # parse and open http://localhost:8765
python3 -m http.server 8765 # serve the page without parsing
```

Open the page over HTTP — `fetch` of the JSON does not work from `file://`.

## Hosting and schedule

GitHub only serves static files (Pages from `main`, root). The page reads `data/stations.json` from this
same repository; the parser runs locally and pushes fresh snapshots:

```sh
./install-schedule.sh       # install the launchd job (default 1800 s = 30 min)
./install-schedule.sh 900   # or a custom interval, in seconds
tail -f logs/update.log     # what the schedule has been doing
```

Removing the schedule:

```sh
launchctl bootout gui/$(id -u)/dev.andy.fuel-update
rm ~/Library/LaunchAgents/dev.andy.fuel-update.plist
```

Updates happen while the Mac is awake; launchd runs a missed job after wake. An open tab re-reads the
JSON every 5 minutes and displays the snapshot age. Requests carry a `?v=<timestamp>` cache buster —
without it the GitHub Pages CDN can serve a stale snapshot.

Note: every run rewrites the JSON (it carries the collection time and `price.since`), so a commit lands
every 30 minutes even when no status changed.

## Why the parser cannot run on GitHub

Verified from a GitHub Actions runner (US): `gpnbonus.ru` is unreachable at the network level — DNS
resolves (213.221.41.242) but the TCP connection to port 443 never completes, and this affects the whole
site, not just the API. Fetching from the visitor's browser fails too: responses carry no
`Access-Control-Allow-Origin` header, so `fetch` dies with `TypeError: Failed to fetch`.

Hence the split: the parser runs locally, GitHub Pages just hosts the result.

## Status logic (mirrors the site)

- `rest.avail == true` → in stock
- `rest.avail == false` and `rest.delivery != "no"` (`yes`/`soon`) → in transit; `soon` renders as
  "(еще ~2ч)", which is the site's own wording — the API returns no numeric ETA
- `rest.avail == false` and `delivery == "no"` → out of stock
- the fuel is missing from the station response → not sold

Each run also diffs against the previous snapshot and stores the status transitions in `changes`, which
the page shows above the list.

## Data shape

`data/stations.json`:

| field | meaning |
| --- | --- |
| `generatedAt`, `previousAt` | collection time of this and the previous snapshot (UTC) |
| `fuel` | the tracked product (`421` = G-95) |
| `total`, `errors` | stations in the snapshot, failed station requests |
| `changes[]` | status transitions since the previous snapshot |
| `stations[].fuel` | price, `status`, `avail`, `since` (MSK), `delivery`, `priceSince` |
| `stations[].allFuels[]` | the same for every fuel sold at the station |

## Fuel ids

`421` G-95, `12` AI-95, `62` AI-92, `21` AI-98, `100032` G-100, `100036` AI-100, `512`/`372`/`374`/`461`
diesel variants, `424` G-DT, `541` DT Opti, `373` LPG, `531` CNG. Pass one with `--fuel`.

Region: `--region 2612765` is Sverdlovsk (default); other ids appear in the `regions` array of the
station-list response.
