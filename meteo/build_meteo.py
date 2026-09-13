#!/usr/bin/env python3
"""Météo du trip moto 14-17 sept. 2026.

Usage :
  python3 build_meteo.py fetch  [--date YYYY-MM-DD]   -> meteo/data.json + tableau lisible sur stdout
  python3 build_meteo.py hourly [--date YYYY-MM-DD]   -> détail heure par heure (ECMWF et Météo-France) pour la prochaine journée
  python3 build_meteo.py render [--date YYYY-MM-DD]   -> meteo/index.html (+ meteo/Meteo_Trip.pdf si un moteur est dispo)
                                                          lit meteo/data.json et meteo/comments.json

comments.json (écrit par l'assistant après lecture du tableau) :
{
  "headline": "phrase de synthèse générale",
  "days": {
    "2026-09-14": {"mood": "sun|hot|rain|cloud|wind", "label": "Grand beau", "badge": "✅ Parfait", "tip": "conseil équipement / vigilance"},
    ...
  },
  "kit": ["conseil 1", "conseil 2", ...]
}
"""
import json, sys, os, subprocess, shutil, statistics, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = "https://fredericvct.github.io/trip-moto-septembre-2026"

DAYS = {
 "2026-09-14": dict(j="J1", title="Brive / Mions → Saint-Nectaire → Puy Mary → Lascelle", route="192 km + 133 km · départ 8h · arrivée ~16h30",
   pts=[("Départ 8h (Saint-Cyr, Mions)",45.22,1.42,"08-10"),("Mauriac",45.22,2.33,"09-11"),
        ("Saint-Nectaire · déjeuner",45.59,2.99,"11-14"),("Puy Mary · Pas de Peyrol (1 589 m)",45.11,2.68,"14-16"),
        ("Lascelle · arrivée",45.02,2.55,"16-18")]),
 "2026-09-15": dict(j="J2", title="Lascelle → Prat de Bouc → Chaudes-Aigues → Garabit → Laguiole", route="238 km · départ 9h · arrivée ~17h",
   pts=[("Départ 9h Lascelle",45.02,2.55,"08-10"),("Col de Prat de Bouc (1 392 m)",45.09,2.80,"09-11"),
        ("Chaudes-Aigues · déjeuner",44.85,3.00,"11-14"),("Garabit · Truyère",44.97,3.18,"13-15"),
        ("Laguiole · arrivée (1 000 m)",44.68,2.85,"15-18")]),
 "2026-09-16": dict(j="J3", title="Laguiole → Vallée du Lot → Entraygues → Conques → Rodez", route="249 km · départ 9h · arrivée ~17h",
   pts=[("Départ 9h Laguiole (1 000 m)",44.68,2.85,"08-10"),("Descente D19 · Espalion · Estaing",44.52,2.76,"10-12"),
        ("Entraygues · déjeuner",44.65,2.56,"12-14"),("Conques",44.60,2.40,"14-15"),
        ("Bozouls · Rodez · arrivée",44.35,2.57,"15-18")]),
 "2026-09-17": dict(j="J4", title="Rodez → Villefranche → Figeac → Saint-Céré → Martel → Saint-Cyr", route="240 km · départ 9h · arrivée ~17h",
   pts=[("Départ 9h Rodez",44.35,2.57,"08-10"),("Villefranche-de-Rouergue",44.35,2.04,"10-11"),
        ("Figeac · déjeuner",44.61,2.03,"12-14"),("Saint-Céré · Martel",44.90,1.75,"14-16"),
        ("Saint-Cyr-la-Roche · arrivée",45.22,1.42,"16-18")]),
}
MODELS = ["ecmwf_ifs025","meteofrance_seamless","icon_seamless","gfs_seamless"]
MODEL_LABEL = {"ecmwf_ifs025":"ECMWF","meteofrance_seamless":"MF","icon_seamless":"ICON","gfs_seamless":"GFS"}
VARS = "temperature_2m,apparent_temperature,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m,wind_direction_10m,weather_code,cloud_cover"
JOURS = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
JOURS_C = {0:"Lun",1:"Mar",2:"Mer",3:"Jeu",4:"Ven",5:"Sam",6:"Dim"}

def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name)+1]
    return default

def today():
    d = arg("--date")
    return datetime.date.fromisoformat(d) if d else datetime.date.today()

def remaining_days(t):
    return [d for d in DAYS if datetime.date.fromisoformat(d) > t]

def fetch_point(lat, lon, date):
    q = dict(latitude=lat, longitude=lon, hourly=VARS, models=",".join(MODELS),
             start_date=date, end_date=date, timezone="Europe/Paris", wind_speed_unit="kmh")
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)

def dirname(deg):
    if deg is None: return ""
    return ["N","NE","E","SE","S","SO","O","NO"][int((deg+22.5)//45) % 8]

def fetch(t):
    out = {"issued": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "today": t.isoformat(), "days": {}}
    for date in remaining_days(t):
        rows = []
        for name, lat, lon, win in DAYS[date]["pts"]:
            d = fetch_point(lat, lon, date); h = d["hourly"]; times = h["time"]
            h0, h1 = [int(x) for x in win.split("-")]
            idx = [i for i, tt in enumerate(times) if h0 <= int(tt[11:13]) <= h1]
            per = {}
            for m in MODELS:
                def g(v):
                    k = f"{v}_{m}"
                    return [h[k][i] for i in idx if h.get(k) and h[k][i] is not None]
                T = g("temperature_2m")
                if not T: continue
                ta = g("apparent_temperature"); p = g("precipitation"); pp = g("precipitation_probability")
                w = g("wind_speed_10m"); gu = g("wind_gusts_10m"); wd = g("wind_direction_10m"); cc = g("cloud_cover"); wc = g("weather_code")
                per[m] = dict(tmin=min(T), tmax=max(T), tapp=min(ta) if ta else None, precip=round(sum(p),1),
                              pprob=max(pp) if pp else None, wind=max(w), gust=max(gu) if gu else None,
                              wdir=statistics.median(wd) if wd else None, cloud=round(sum(cc)/len(cc)) if cc else None,
                              wc=max(wc) if wc else None)
            def med(k):
                v = [x[k] for x in per.values() if x.get(k) is not None]
                return round(statistics.median(v), 1) if v else None
            def mx(k):
                v = [x[k] for x in per.values() if x.get(k) is not None]
                return max(v) if v else None
            precips = [x["precip"] for x in per.values()]
            rows.append(dict(name=name, win=win, elev=d.get("elevation"),
                tmin=med("tmin"), tmax=med("tmax"), tapp=med("tapp"),
                precip_med=med("precip"), precip_max=mx("precip"), pprob=mx("pprob"),
                wind=med("wind"), gust=mx("gust"), wdir=dirname(med("wdir")), cloud=med("cloud"),
                models=per, disagree=(max(precips)-min(precips) >= 1.5) if precips else False))
        out["days"][date] = rows
    return out

def print_table(data):
    print(f"Prévisions émises le {data['issued']} (aujourd'hui {data['today']})")
    for date, rows in data["days"].items():
        dd = datetime.date.fromisoformat(date)
        print(f"\n=== {DAYS[date]['j']} {JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d} · {DAYS[date]['title']} ===")
        print(f"{'Étape':42s} {'T min/max':10s} {'ress.':6s} {'pluie med/max':14s} {'prob':5s} {'vent/raf':10s} {'dir':4s} {'nuage':6s}")
        for r in rows:
            print(f"{r['name']:42s} {r['tmin']:4.1f}/{r['tmax']:4.1f}  {str(r['tapp']):6s} {str(r['precip_med']):5s}/{str(r['precip_max']):7s} {str(r['pprob'])+'%':5s} {r['wind']:3.0f}/{r['gust'] or 0:3.0f}     {r['wdir']:4s} {str(r['cloud'])+'%':6s}" + ("  ⚠ modèles en désaccord sur la pluie" if r["disagree"] else ""))
            print("      détail : " + "  ".join(f"{MODEL_LABEL[m]} {v['tmin']:.0f}/{v['tmax']:.0f}° {v['precip']}mm {v['pprob'] if v['pprob'] is not None else '-'}% raf{v['gust'] or 0:.0f}" for m, v in r["models"].items()))

def hourly(t):
    days = remaining_days(t)
    if not days: print("Plus de journée à venir."); return
    date = days[0]
    print(f"Détail horaire {DAYS[date]['j']} {date} · ECMWF | Météo-France  (T°, pluie mm, prob %, vent/raf km/h, dir)")
    for name, lat, lon, win in DAYS[date]["pts"]:
        h = fetch_point(lat, lon, date)["hourly"]
        print(f"\n-- {name} (créneau {win}h) --")
        for i, tt in enumerate(h["time"]):
            hh = int(tt[11:13])
            if 7 <= hh <= 19:
                def v(k, m):
                    x = h.get(f"{k}_{m}"); return x[i] if x and x[i] is not None else None
                e = lambda k: v(k, "ecmwf_ifs025"); m = lambda k: v(k, "meteofrance_seamless")
                f = lambda x, fmt: (fmt % x) if x is not None else "  -"
                print(f"{hh:02d}h  ECMWF {f(e('temperature_2m'),'%4.1f')}° {f(e('precipitation'),'%4.1f')}mm {f(e('precipitation_probability'),'%3.0f')}% {f(e('wind_speed_10m'),'%3.0f')}/{f(e('wind_gusts_10m'),'%3.0f')} {dirname(e('wind_direction_10m')):2s}"
                      f"  | MF {f(m('temperature_2m'),'%4.1f')}° {f(m('precipitation'),'%4.1f')}mm {f(m('wind_speed_10m'),'%3.0f')}/{f(m('wind_gusts_10m'),'%3.0f')} {dirname(m('wind_direction_10m')):2s}")

# ---------- rendu ----------
MOOD = {"sun":("☀️","#f2a516"), "hot":("🌞","#e9821b"), "rain":("🌧️","#6b7d8f"), "cloud":("⛅","#8aa4bd"), "wind":("💨","#7a8fa6"), "storm":("⛈️","#5a6b7c")}

def pill(txt, kind):
    col = {"ok":("#e2f5e6","#1b7a34"), "warn":("#fff1cf","#9a6300"), "bad":("#ffe0e0","#b52323")}[kind]
    return f'<span style="display:inline-block;border-radius:20px;padding:2px 9px;font-weight:700;font-size:12px;background:{col[0]};color:{col[1]};white-space:nowrap">{txt}</span>'

def rain_pill(r):
    p = r["pprob"] or 0; mm = r["precip_max"] or 0
    if p < 20 and mm < 0.5: return pill("0 %" if p < 5 else f"{p} %", "ok")
    if p < 50 and mm < 3: return pill(f"{p} % · {mm} mm" + (" · désaccord" if r["disagree"] else ""), "warn")
    return pill(f"{p} % · {mm} mm", "bad")

def wind_txt(r):
    w = r["wind"] or 0; g = r["gust"] or 0
    txt = f"{r['wdir']} {w:.0f} / raf. {g:.0f} km/h" if g else f"{w:.0f} km/h"
    if g >= 45: return pill(txt, "bad")
    if g >= 35: return pill(txt, "warn")
    if w < 8 and g < 20: return "faible"
    return txt

def temp_txt(r):
    t = f"{r['tmin']:.0f}–{r['tmax']:.0f}°" if abs(r['tmax']-r['tmin']) >= 1 else f"{r['tmax']:.0f}°"
    if r["tapp"] is not None and r["tapp"] <= 12 and r["tmin"] - r["tapp"] >= 1.5:
        t += f' <span style="font-weight:400;font-size:11px">(ressenti {r["tapp"]:.0f}°)</span>'
    return t

def render(data, com):
    t = datetime.date.fromisoformat(data["today"])
    days = list(data["days"].keys())
    first = days[0] if days else None
    F = "font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;"
    H = []
    H.append(f'<div style="{F}max-width:720px;margin:0 auto;color:#1b2733;font-size:13.5px">')
    H.append(f'<div style="background:#1A3A5C;color:#fff;border-radius:14px;padding:16px 20px">'
             f'<div style="font-size:24px;font-weight:800">🏍️ Météo Trip Moto · 14 → 17 sept. 2026</div>'
             f'<div style="opacity:.9;font-size:13px;margin-top:4px">Point du {data["issued"]} · ECMWF + Météo-France AROME, recoupés ICON/GFS</div></div>')
    if com.get("headline"):
        H.append(f'<div style="background:#eef4fa;border-left:5px solid #2f6ea0;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px"><b>En résumé :</b> {com["headline"]}</div>')
    # vue d'ensemble
    H.append('<table cellpadding="0" cellspacing="6" style="width:100%;border-collapse:separate;margin:8px 0"><tr>')
    for d in days:
        dd = datetime.date.fromisoformat(d); c = com["days"].get(d, {}); ic, col = MOOD.get(c.get("mood","cloud"), MOOD["cloud"])
        rows = data["days"][d]; tmin = min(r["tmin"] for r in rows); tmax = max(r["tmax"] for r in rows)
        H.append(f'<td style="background:{col};color:#fff;border-radius:12px;padding:10px 6px;text-align:center;width:{100//max(len(days),1)}%">'
                 f'<div style="font-size:30px">{ic}</div><div style="font-weight:700;font-size:14px">{JOURS_C[dd.weekday()]} {dd.day}</div>'
                 f'<div style="font-size:12px">{c.get("label","")}</div><div style="font-size:18px;font-weight:800">{tmin:.0f} → {tmax:.0f}°</div></td>')
    H.append('</tr></table>')
    # fiches
    for d in days:
        dd = datetime.date.fromisoformat(d); c = com["days"].get(d, {}); ic, col = MOOD.get(c.get("mood","cloud"), MOOD["cloud"])
        demain = " · DEMAIN" if d == first and (dd - t).days == 1 else ""
        H.append(f'<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden">'
                 f'<div style="background:{col};color:#fff;padding:9px 14px"><table cellpadding="0" cellspacing="0" style="width:100%"><tr>'
                 f'<td style="font-size:28px;width:40px">{ic}</td><td><div style="font-weight:800;font-size:16px">{DAYS[d]["j"]} · {JOURS[dd.weekday()]} {dd.day}{demain} · {DAYS[d]["title"]}</div>'
                 f'<div style="font-size:12px;opacity:.95">{DAYS[d]["route"]}</div></td>'
                 f'<td style="text-align:right;white-space:nowrap"><span style="background:rgba(255,255,255,.25);border-radius:20px;padding:4px 12px;font-weight:700;font-size:13px">{c.get("badge","")}</span></td></tr></table></div>')
        H.append('<table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">'
                 '<tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">ÉTAPE</th>'
                 '<th style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px">🌡️ TEMP.</th><th style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px">🌧️ PLUIE</th>'
                 '<th style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px">💨 VENT</th></tr>')
        for r in data["days"][d]:
            H.append(f'<tr><td style="padding:5px 10px;border-top:1px solid #eef2f6;font-weight:600">{r["name"]}</td>'
                     f'<td style="padding:5px 4px;border-top:1px solid #eef2f6;text-align:center;font-weight:800;font-size:15px;white-space:nowrap">{temp_txt(r)}</td>'
                     f'<td style="padding:5px 4px;border-top:1px solid #eef2f6;text-align:center">{rain_pill(r)}</td>'
                     f'<td style="padding:5px 4px;border-top:1px solid #eef2f6;text-align:center;white-space:nowrap">{wind_txt(r)}</td></tr>')
        H.append('</table>')
        if c.get("tip"):
            H.append(f'<div style="background:#f4f7fa;padding:8px 14px;font-size:12.5px;border-top:1px solid #e3eaf1">{c["tip"]}</div>')
        H.append('</div>')
    if com.get("kit"):
        H.append('<table cellpadding="0" cellspacing="6" style="width:100%"><tr>')
        for i, k in enumerate(com["kit"]):
            if i and i % 2 == 0: H.append('</tr><tr>')
            H.append(f'<td style="background:#f4f7fa;border-radius:10px;padding:8px 12px;font-size:12.5px;width:50%;vertical-align:top">{k}</td>')
        H.append('</tr></table>')
    H.append(f'<div style="font-size:10.5px;color:#6b7d8f;margin-top:10px;text-align:center">Source : Open-Meteo · ECMWF IFS 0.25°, Météo-France AROME/ARPEGE, ICON, GFS · '
             f'<a href="{PAGES}/">Parcours</a> · <a href="{PAGES}/meteo/">Version web</a> · <a href="{PAGES}/meteo/Meteo_Trip.pdf">PDF</a></div></div>')
    body = "\n".join(H)
    page = ('<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Météo Trip Moto</title><style>@page{size:210mm 470mm;margin:8mm} body{margin:0;padding:10px;background:#fff} th{text-transform:uppercase;letter-spacing:.3px}</style></head>'
            f'<body>{body}</body></html>')
    return body, page

def make_pdf(html_path, pdf_path):
    for exe in ["google-chrome", "chromium", "chromium-browser", "chrome",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        p = shutil.which(exe) or (exe if os.path.exists(exe) else None)
        if p:
            r = subprocess.run([p, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                                f"--print-to-pdf={pdf_path}", f"file://{html_path}"], capture_output=True, timeout=120)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
                return "chrome"
    try:
        import weasyprint  # noqa
        weasyprint.HTML(html_path).write_pdf(pdf_path)
        return "weasyprint"
    except Exception as e:
        print("PDF non généré :", e)
    return None

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    t = today()
    if cmd == "fetch":
        data = fetch(t)
        json.dump(data, open(os.path.join(HERE, "data.json"), "w"), ensure_ascii=False, indent=1)
        print_table(data)
        if not data["days"]:
            print("PLUS AUCUNE JOURNÉE À VENIR : rien à faire.")
    elif cmd == "hourly":
        hourly(t)
    elif cmd == "render":
        data = json.load(open(os.path.join(HERE, "data.json")))
        com = json.load(open(os.path.join(HERE, "comments.json")))
        body, page = render(data, com)
        open(os.path.join(HERE, "index.html"), "w").write(page)
        open(os.path.join(HERE, "email.html"), "w").write(body)
        pdf = os.path.join(HERE, "Meteo_Trip.pdf")
        eng = make_pdf(os.path.join(HERE, "index.html"), pdf)
        print("index.html + email.html écrits ;", f"PDF via {eng} ({os.path.getsize(pdf)//1024} Ko)" if eng else "pas de PDF")
    else:
        print(__doc__)
