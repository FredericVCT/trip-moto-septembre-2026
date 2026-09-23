#!/usr/bin/env python3
"""Séjour au Buron de la Tâche (Mont-Dore, 5 au 7 octobre 2026) : modèles déterministes + ensembles (Open-Meteo) -> meteo-buron/raw.json

Deux points : le gîte (1 240 m) et le sommet du Puy de Sancy (1 886 m, pour les crêtes).
"""
import json, os, time, urllib.request, urllib.parse, urllib.error, datetime

SITES = {
    "gite":   dict(latitude=45.5971, longitude=2.8311, elevation=1240),   # 719 route de la Tâche, Mont-Dore
    "sommet": dict(latitude=45.5285, longitude=2.8141, elevation=1886),   # Puy de Sancy
}
HERE = os.path.dirname(os.path.abspath(__file__))
DET = ["arome_france", "meteofrance_seamless", "ecmwf_ifs025", "ecmwf_aifs025_single",
       "icon_seamless", "gfs_seamless", "ukmo_seamless"]
ENS = ["ecmwf_ifs025", "ecmwf_aifs025", "icon_seamless", "gfs025"]
HOURLY = ("precipitation,snowfall,weather_code,cloud_cover,cloud_cover_low,temperature_2m,apparent_temperature,"
          "wind_speed_10m,wind_gusts_10m,freezing_level_height")

def get(url):
    last = None
    for d in (0, 5, 15, 30):
        if d: time.sleep(d)
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"{e.code} {e.read()[:200]!r}"
            if e.code == 400: break   # requête refusée : inutile d'insister
        except Exception as e:
            last = e
    return {"error": str(last)}

out = {"issued_utc": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "sites": SITES, "det": {}, "ens": {}}
for s, p in SITES.items():
    out["det"][s], out["ens"][s] = {}, {}
    for m in DET:
        q = dict(p, models=m, timezone="Europe/Paris", forecast_days=16, hourly=HOURLY)
        out["det"][s][m] = get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q))
    for m in ENS:
        q = dict(p, models=m, timezone="Europe/Paris", forecast_days=16, hourly="precipitation,temperature_2m")
        out["ens"][s][m] = get("https://ensemble-api.open-meteo.com/v1/ensemble?" + urllib.parse.urlencode(q))
q = dict(SITES["gite"], timezone="Europe/Paris", forecast_days=16, daily="sunrise,sunset")
out["sun"] = get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q))
json.dump(out, open(os.path.join(HERE, "raw.json"), "w"))
for k in ("det", "ens"):
    for s in SITES:
        for m, d in out[k][s].items():
            print(k, s, m, "ERREUR " + d["error"] if "error" in d else len(d.get("hourly", {})))
