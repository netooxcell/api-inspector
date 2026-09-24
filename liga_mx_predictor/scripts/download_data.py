"""
Descarga reproducible de datos externos de Liga MX.

Fuentes (ver reports/DATA_SOURCES.md para detalle completo):
  1. footballcsv/mexico (GitHub, CC0)   -> resultados históricos por temporada
  2. TheSportsDB (API pública, key "3") -> temporada actual, próximos partidos, tabla

No sobrescribe corridas anteriores: cada descarga se guarda con la fecha de
descarga en el nombre del manifiesto, y los raw files siempre representan la
última descarga exitosa de cada fuente (regla: nunca modificar datos crudos
a mano).

Uso:
    python scripts/download_data.py
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_FOOTBALLCSV = ROOT / "data" / "raw" / "footballcsv"
RAW_SPORTSDB = ROOT / "data" / "raw" / "thesportsdb"
MANIFEST_PATH = ROOT / "data" / "raw" / "download_manifest.json"

FOOTBALLCSV_BASE = "https://raw.githubusercontent.com/footballcsv/mexico/master"
# footballcsv publishes one season folder per year, named "YYYY-YY" (Jul-Jun),
# with a Liga MX first-division file at "<season>/mx.1.csv".
SEASONS = [f"{y}-{str(y + 1)[2:]}" for y in range(2000, 2025)]  # 2000-01 .. 2024-25

SPORTSDB_KEY = "3"  # public test key documented at thesportsdb.com/free_sports_api
SPORTSDB_BASE = f"https://www.thesportsdb.com/api/v1/json/{SPORTSDB_KEY}"
LIGA_MX_LEAGUE_ID = "4350"  # Mexican Primera League / Liga MX
CURRENT_SEASON = "2026-2027"
CURRENT_SEASON_ROUNDS = range(1, 21)  # covers the full Apertura 2026 regular phase + margin

HEADERS = {"User-Agent": "liga-mx-predictor/1.0 (data audit script)"}
TIMEOUT = 30


def _get(url, retries=3, backoff=2):
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            return resp
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"Failed to GET {url}: {last_err}")


def download_footballcsv():
    RAW_FOOTBALLCSV.mkdir(parents=True, exist_ok=True)
    results = []
    for season in SEASONS:
        url = f"{FOOTBALLCSV_BASE}/{season}/mx.1.csv"
        resp = _get(url)
        if resp.status_code == 200 and resp.text.strip():
            out_path = RAW_FOOTBALLCSV / f"{season}.csv"
            out_path.write_text(resp.text, encoding="utf-8")
            results.append({"season": season, "status": "ok", "rows": resp.text.count("\n"), "url": url})
            print(f"[footballcsv] {season}: OK ({resp.text.count(chr(10))} lines)")
        else:
            results.append({"season": season, "status": f"missing (HTTP {resp.status_code})", "url": url})
            print(f"[footballcsv] {season}: not available (HTTP {resp.status_code}) - skipping")
    return results


def download_sportsdb():
    RAW_SPORTSDB.mkdir(parents=True, exist_ok=True)
    # NOTE: lookup_all_teams.php is intentionally excluded — with the free
    # test key ("3") it ignores the `id` param and returns an unrelated
    # English lower-league demo list (verified 2026-08-14). Team identities
    # are instead derived from standings/events, which return correct data.
    endpoints = {
        "past_events": f"{SPORTSDB_BASE}/eventspastleague.php?id={LIGA_MX_LEAGUE_ID}",
        "next_events": f"{SPORTSDB_BASE}/eventsnextleague.php?id={LIGA_MX_LEAGUE_ID}",
        "standings": f"{SPORTSDB_BASE}/lookuptable.php?l={LIGA_MX_LEAGUE_ID}&s=2025-2026",
    }
    results = []
    for name, url in endpoints.items():
        resp = _get(url)
        out_path = RAW_SPORTSDB / f"{name}.json"
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                results.append({"endpoint": name, "status": f"invalid JSON (HTTP {resp.status_code})", "url": url})
                print(f"[thesportsdb] {name}: invalid JSON - skipping")
                continue
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            n_items = len(next(iter(data.values())) or []) if isinstance(data, dict) and data else 0
            results.append({"endpoint": name, "status": "ok", "items": n_items, "url": url})
            print(f"[thesportsdb] {name}: OK ({n_items} items)")
        else:
            results.append({"endpoint": name, "status": f"HTTP {resp.status_code}", "url": url})
            print(f"[thesportsdb] {name}: HTTP {resp.status_code} - skipping")

    # eventsround.php returns every event (played + scheduled) for a given
    # round of the *current* season — unlike eventspastleague/eventsnextleague
    # (each capped at 1 item on the free key), this endpoint is not capped
    # the same way, so it is the only reliable way to get more than a single
    # match of real current-season data from this free tier.
    all_round_events = []
    for r in CURRENT_SEASON_ROUNDS:
        url = f"{SPORTSDB_BASE}/eventsround.php?id={LIGA_MX_LEAGUE_ID}&r={r}&s={CURRENT_SEASON}"
        resp = _get(url)
        if resp.status_code != 200:
            results.append({"endpoint": f"round_{r}", "status": f"HTTP {resp.status_code}", "url": url})
            continue
        try:
            data = resp.json()
        except ValueError:
            results.append({"endpoint": f"round_{r}", "status": "invalid JSON", "url": url})
            continue
        events = data.get("events") or []
        all_round_events.extend(events)
        results.append({"endpoint": f"round_{r}", "status": "ok", "items": len(events), "url": url})
        print(f"[thesportsdb] round {r}: OK ({len(events)} events)")
        if not events:
            break  # no more scheduled rounds beyond this point

    (RAW_SPORTSDB / "current_season_rounds.json").write_text(
        json.dumps({"events": all_round_events}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[thesportsdb] current_season_rounds: {len(all_round_events)} total events saved")
    return results


def main():
    downloaded_at = datetime.now(timezone.utc).isoformat()
    footballcsv_results = download_footballcsv()
    sportsdb_results = download_sportsdb()

    manifest = {
        "downloaded_at_utc": downloaded_at,
        "footballcsv": footballcsv_results,
        "thesportsdb": sportsdb_results,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_seasons = sum(1 for r in footballcsv_results if r["status"] == "ok")
    ok_endpoints = sum(1 for r in sportsdb_results if r["status"] == "ok")
    print(f"\nResumen: footballcsv {ok_seasons}/{len(SEASONS)} temporadas OK, "
          f"thesportsdb {ok_endpoints}/{len(sportsdb_results)} endpoints OK.")
    print(f"Manifiesto guardado en {MANIFEST_PATH}")

    if ok_seasons == 0 and ok_endpoints == 0:
        print("ERROR: ninguna fuente respondió correctamente.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
