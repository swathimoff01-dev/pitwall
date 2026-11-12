"""Spike: look at what OpenF1 returns for one race. Free, no account, polite pacing."""

import time

import httpx

BASE = "https://api.openf1.org/v1"
GAP_S = 2.5  # one call every 2.5s = 24/min, under the 30/min limit


def get(client: httpx.Client, endpoint: str, **params):
    for attempt in range(5):
        time.sleep(GAP_S)
        resp = client.get(f"{BASE}/{endpoint}", params=params, timeout=60)
        if resp.status_code == 404:  # OpenF1 uses 404 for "no rows"
            return []
        if resp.status_code == 429:
            wait = 20 * (attempt + 1)
            print(f"429 slow down; waiting {wait}s")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Giving up on {endpoint}")


def show(label: str, rows: list) -> None:
    print(f"\n--- {label}: {len(rows)} rows ---")
    if rows:
        print("fields:", sorted(rows[0].keys()))
        print("first row:", rows[0])


with httpx.Client(headers={"User-Agent": "pitwall-portfolio/0.1"}) as c:
    races_2023 = get(c, "sessions", year=2023, session_name="Race")
    show("2023 race sessions", races_2023)

    # Coverage check: should be empty if the free history really starts in 2023
    print("\n2022 race sessions:", len(get(c, "sessions", year=2022, session_name="Race")))

    spain = next(s for s in races_2023 if s.get("country_name") == "Spain")
    key = spain["session_key"]
    print("\nSpanish GP 2023 session_key:", key)

    show("drivers", get(c, "drivers", session_key=key))
    show("laps (driver 1 = Verstappen)", get(c, "laps", session_key=key, driver_number=1))
    show("stints", get(c, "stints", session_key=key))
    show("pit", get(c, "pit", session_key=key))
    show("race_control", get(c, "race_control", session_key=key))