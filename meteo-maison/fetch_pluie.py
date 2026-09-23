#!/usr/bin/env python3
"""Pluie à Saint-Cyr-la-Roche : modèles déterministes + ensembles (Open-Meteo) -> meteo-maison/raw.json"""
import json, os, time, urllib.request, urllib.parse, datetime

LAT, LON = 45.259, 1.371   # Saint-Cyr-la-Roche (Corrèze)
HERE = os.path.dirname(os.path.abspath(__file__))
DET = ["arome_france", "arome_france_hd", "meteofrance_seamless", "ecmwf_ifs025", "ecmwf_aifs025_single",
       "icon_d2", "icon_eu", "icon_seamless", "gfs_seamless", "ukmo_seamless"]
ENS = ["ecmwf_ifs025", "ecmwf_aifs025", "icon_seamless", "gfs025", "meteofrance_arpege_world"]

def get(url):
    last = None
    for d in (0, 5, 15, 30):
        if d: time.sleep(d)
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            last = e
    return {"error": str(last)}

out = {"issued_utc": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "lat": LAT, "lon": LON, "det": {}, "ens": {}}
for m in DET:
    q = dict(latitude=LAT, longitude=LON, models=m, timezone="Europe/Paris", forecast_days=10,
             hourly="precipitation,precipitation_probability,rain,showers,weather_code,cloud_cover,temperature_2m,wind_gusts_10m")
    out["det"][m] = get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q))
for m in ENS:
    q = dict(latitude=LAT, longitude=LON, models=m, timezone="Europe/Paris", forecast_days=10, hourly="precipitation")
    out["ens"][m] = get("https://ensemble-api.open-meteo.com/v1/ensemble?" + urllib.parse.urlencode(q))
json.dump(out, open(os.path.join(HERE, "raw.json"), "w"))
for k in ("det", "ens"):
    for m, d in out[k].items():
        print(k, m, "ERREUR " + d["error"] if "error" in d else len(d.get("hourly", {})))
