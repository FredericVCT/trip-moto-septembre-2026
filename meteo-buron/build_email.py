#!/usr/bin/env python3
"""Briefing météo du séjour au Buron de la Tâche (Mont-Dore), du lundi 5 au mercredi 7 octobre 2026.

Usage :
  python3 build_email.py summary    -> calcule meteo-buron/summary.json à partir de raw.json, l'affiche,
                                        et liste les écarts avec sent.json (dernier briefing envoyé)
  python3 build_email.py render     -> meteo-buron/email.html à partir de summary.json + comments.json
  python3 build_email.py mark-sent  -> copie summary.json vers sent.json et l'ajoute à history.json

comments.json (rédigé par l'assistant après lecture de `summary`) :
{
  "headline": "synthèse (HTML léger), sur les 3 jours du séjour",
  "changes": "interprétation des écarts avec le briefing précédent (vide s'il n'y en a pas)",
  "agreement": "accord ou désaccord des modèles, fiabilité selon l'échéance (HTML léger)",
  "trip": {"2026-10-05": ["sun|cloud|rain|wind|storm|fog|cold", "libellé 2 à 5 mots", "badge 1 à 3 mots",
                          "conseil activité (HTML léger, 1 à 3 phrases)"], ... 3 entrées},
  "tips": ["conseil 1", "conseil 2", ...]
}
"""
import json, os, sys, shutil, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
TRIP = {  # jour: (libellé, début et fin du créneau d'activité, programme)
    "2026-10-05": ("J1 lun 5/10", 14, 20, "Arrivée 14h, lac de Guéry puis col de la Croix-Morand"),
    "2026-10-06": ("J2 mar 6/10", 8, 19, "VTT 28 km 9h30-13h30 (Guéry, Servières, Pessade, point haut 1 470 m), repos l'après-midi"),
    "2026-10-07": ("J3 mer 7/10", 10, 17, "Départ 10h, dernière rando (Banne d'Ordanche)"),
}
LAST = max(TRIP)
JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
LAB = {"arome_france": "AROME", "meteofrance_seamless": "Météo-France", "ecmwf_ifs025": "ECMWF", "ecmwf_aifs025_single": "AIFS",
       "icon_seamless": "ICON", "gfs_seamless": "GFS", "ukmo_seamless": "UKMO"}
MOOD = {"sun": ("☀️", "#e39b12"), "cloud": ("⛅", "#7f9ab5"), "rain": ("🌧️", "#5f7285"), "wind": ("💨", "#6f8499"),
        "storm": ("⛈️", "#4f5f70"), "fog": ("🌫️", "#8d99a6"), "cold": ("🥶", "#4a86b8")}
d = json.load(open(os.path.join(HERE, "raw.json")))

def window(h, key, day, a=0, b=24):
    """Valeurs horaires de h[key] pour day entre a h et b h, ou None si le modèle ne couvre pas tout le créneau."""
    v = [x for t, x in zip(h["time"], h[key]) if t[:10] == day and a <= int(t[11:13]) < b and x is not None]
    return v if len(v) == b - a else None

def members(site, var):
    """Liste de séries horaires (h, clé) de tous les membres d'ensemble disponibles."""
    out = []
    for m, v in d["ens"][site].items():
        h = v.get("hourly")
        if not h: continue
        out += [(h, k) for k in h if k == var or k.startswith(var + "_member")]
    return out

def pct(xs, thr): return round(100 * sum(x >= thr for x in xs) / len(xs)) if xs else None
def med(xs): return round(st.median(xs), 1) if xs else None
def p90(xs): return round(sorted(xs)[int(.9 * (len(xs) - 1))], 1) if xs else None

def det_stat(site, var, day, a, b, fn):
    """fn appliquée au créneau pour chaque modèle déterministe qui le couvre -> {modèle: valeur}"""
    r = {}
    for m in LAB:
        h = d["det"][site].get(m, {}).get("hourly")
        if not h or var not in h: continue
        v = window(h, var, day, a, b)
        if v: r[m] = fn(v)
    return r

def compute(day, today):
    lead = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(today)).days
    P = members("gite", "precipitation")
    tot = [sum(v) for h, k in P if (v := window(h, k, day))]
    if not tot: return None
    r = dict(day=day, lead=lead, n=len(tot), p1=pct(tot, 1), med=med(tot), p90=p90(tot))
    Tg = members("gite", "temperature_2m")
    r["tmin"] = med([min(v) for h, k in Tg if (v := window(h, k, day, 0, 9))])
    r["tmax"] = med([max(v) for h, k in Tg if (v := window(h, k, day, 9, 19))])
    r["det"] = {LAB[m]: round(x, 1) for m, x in det_stat("gite", "precipitation", day, 0, 24, sum).items()}
    if day not in TRIP: return r
    _, a, b, _ = TRIP[day]
    win = [sum(v) for h, k in P if (v := window(h, k, day, a, b))]
    r["pwin"] = pct(win, .5)
    r["blocks"] = {n: pct([sum(v) for h, k in P if (v := window(h, k, day, x, y))], .5)
                   for n, (x, y) in {"matin 8-12h": (8, 12), "après-midi 12-18h": (12, 18), "soir 18-22h": (18, 22)}.items()}
    Ts = members("sommet", "temperature_2m")
    r["s_tmin"] = med([min(v) for h, k in Ts if (v := window(h, k, day, 9, 18))])
    r["s_tmax"] = med([max(v) for h, k in Ts if (v := window(h, k, day, 9, 18))])
    ds = lambda var, fn, site="sommet", a=9, b=18: det_stat(site, var, day, a, b, fn)
    def cons(x):  # médiane des modèles déterministes + détail
        return (round(st.median(x.values())) if x else None, {LAB[m]: round(v) for m, v in x.items()})
    r["s_gust"], r["s_gust_det"] = cons(ds("wind_gusts_10m", max))
    r["s_wind"], _ = cons(ds("wind_speed_10m", lambda v: sum(v) / len(v)))
    r["s_feel"], r["s_feel_det"] = cons(ds("apparent_temperature", min))
    r["s_low"], _ = cons(ds("cloud_cover_low", lambda v: sum(v) / len(v)))
    r["g_low"], _ = cons(ds("cloud_cover_low", lambda v: sum(v) / len(v), "gite", a, b))
    r["g_gust"], _ = cons(ds("wind_gusts_10m", max, "gite", a, b))
    r["frost"], _ = cons(ds("temperature_2m", min, "gite", 0, 9))
    r["iso0"], _ = cons(ds("freezing_level_height", min, "gite", 0, 24))
    r["snow"], _ = cons(ds("snowfall", sum, "sommet", 0, 24))
    sun = d.get("sun", {}).get("daily", {})
    if day in sun.get("time", []):
        i = sun["time"].index(day); r["sunrise"], r["sunset"] = sun["sunrise"][i][11:16], sun["sunset"][i][11:16]
    return r

def issued_local():
    u = datetime.datetime.strptime(d["issued_utc"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
    from zoneinfo import ZoneInfo
    return u.astimezone(ZoneInfo("Europe/Paris"))

def confidence(lead):
    return ("fiable" if lead <= 2 else "bonne" if lead <= 5 else "moyenne, tendance" if lead <= 9 else "faible, simple tendance")

def summary():
    iss = issued_local(); today = iss.date().isoformat()
    days, day = [], datetime.date.fromisoformat(today) + datetime.timedelta(days=1)
    while day.isoformat() <= LAST:
        r = compute(day.isoformat(), today)
        if r: days.append(r)
        day += datetime.timedelta(days=1)
    out = {"issued": iss.strftime("%d/%m/%Y %H:%M"), "today": today, "rows": days}
    print(f"Données émises le {out['issued']} (heure de Paris)\n")
    print("AVANT LE SÉJOUR (gîte 1 240 m) : jour, risque >= 1 mm, cumul médian (p90), T min/max")
    for r in days:
        if r["day"] not in TRIP:
            print(f"  {r['day']}  {r['p1']:>3} %  {r['med']} ({r['p90']}) mm  {r['tmin']}/{r['tmax']}°  | " + " · ".join(f"{k} {v}" for k, v in r["det"].items()))
    for r in days:
        if r["day"] not in TRIP: continue
        lab, a, b, prog = TRIP[r["day"]]
        print(f"\n=== {lab} ({prog}) · échéance J+{r['lead']} · confiance {confidence(r['lead'])} · {r['n']} scénarios")
        print(f"  Pluie gîte : risque >= 1 mm sur la journée {r['p1']} %, cumul médian {r['med']} mm (p90 {r['p90']}) ; créneau {a}-{b}h : risque >= 0,5 mm {r['pwin']} %")
        print("  Par tranche (>= 0,5 mm) : " + " · ".join(f"{k} {v} %" for k, v in r["blocks"].items() if v is not None))
        print("  Modèles (cumul jour, mm) : " + " · ".join(f"{k} {v}" for k, v in r["det"].items()))
        print(f"  Gîte : T mini nuit {r['tmin']}° (modèles {r['frost']}°), maxi {r['tmax']}° ; nuages bas {r['g_low']} % ; rafales {r['g_gust']} km/h ; iso 0° mini {r['iso0']} m")
        print(f"  Sommet Sancy 9-18h : T {r['s_tmin']} à {r['s_tmax']}°, ressenti mini {r['s_feel']}° {r['s_feel_det']}, vent moyen {r['s_wind']} km/h, rafales {r['s_gust']} km/h {r['s_gust_det']}, nuages bas {r['s_low']} %, neige {r['snow']} cm")
        print(f"  Soleil : lever {r.get('sunrise')}, coucher {r.get('sunset')}")
    ps = os.path.join(HERE, "sent.json")
    if os.path.exists(ps):
        old = json.load(open(ps)); out["prev_issued"] = old["issued"]
        orow = {r["day"]: r for r in old["rows"]}; lines = []
        for r in days:
            o = orow.get(r["day"])
            if not o or r["day"] not in TRIP: continue
            parts = []
            def chk(k, thr, label, unit):
                if r.get(k) is not None and o.get(k) is not None and abs(r[k] - o[k]) >= thr:
                    parts.append(f"{label} {o[k]}{unit} → {r[k]}{unit}")
            chk("p1", 15, "risque de pluie", " %"); chk("pwin", 15, "risque sur le créneau d'activité", " %")
            chk("med", 2, "cumul médian", " mm"); chk("p90", 5, "cumul p90", " mm")
            chk("tmax", 3, "T maxi gîte", "°"); chk("tmin", 3, "T mini nuit", "°")
            chk("s_feel", 4, "ressenti au sommet", "°"); chk("s_gust", 15, "rafales au sommet", " km/h")
            chk("s_low", 30, "nuages bas au sommet", " %")
            if parts: lines.append(f"{TRIP[r['day']][0]} : " + " ; ".join(parts))
        out["changes"] = lines
        print(f"\nÉcarts depuis le briefing du {old['issued']} :")
        print("\n".join("  - " + l for l in lines) if lines else "  aucun écart notable")
    else:
        print("\nPas de briefing précédent (sent.json absent) : c'est le premier.")
    json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1)

def pill(txt, p, lo=20, hi=50):
    if p is None: return '<span style="color:#8a99a8">n.d.</span>'
    bg, fg = ("#e2f5e6", "#1b7a34") if p < lo else (("#fff1cf", "#9a6300") if p < hi else ("#ffe0e0", "#b52323"))
    return f'<span style="display:inline-block;border-radius:20px;padding:2px 9px;font-weight:700;font-size:12px;background:{bg};color:{fg};white-space:nowrap">{txt}</span>'

def render():
    summ = json.load(open(os.path.join(HERE, "summary.json")))
    com = json.load(open(os.path.join(HERE, "comments.json")))
    hist_path = os.path.join(HERE, "history.json")
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []
    rows = {r["day"]: r for r in summ["rows"]}
    f = lambda x: "n.d." if x is None else f"{x:g}".replace(".", ",")
    box = 'border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden'
    th = 'style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px;text-align:center"'
    td = 'style="padding:6px 6px;border-top:1px solid #eef2f6;text-align:center"'
    tdl = 'style="padding:6px 10px;border-top:1px solid #eef2f6;text-align:left"'
    H = ['<div style="font-family:-apple-system,\'Helvetica Neue\',Arial,sans-serif;max-width:720px;margin:0 auto;color:#1b2733;font-size:13.5px">']
    H.append(f'<div style="background:#1A3A5C;color:#fff;border-radius:14px;padding:16px 20px"><div style="font-size:23px;font-weight:800">🏔️ Buron de la Tâche · Mont-Dore</div><div style="opacity:.92;font-size:13px;margin-top:4px">Séjour du lundi 5 au mercredi 7 octobre · point du {summ["issued"]}<br>Gîte 1 240 m et crêtes du Sancy 1 886 m · 7 modèles + ensembles ECMWF, AIFS, ICON, GFS</div></div>')
    H.append('<div style="background:#eef4fa;border-left:5px solid #2f6ea0;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px"><b>En résumé :</b> ' + com["headline"] + '</div>')
    if com.get("changes") or summ.get("changes"):
        auto = "".join(f"<li>{l}</li>" for l in summ.get("changes", []))
        H.append('<div style="background:#fff8e6;border-left:5px solid #e9a21b;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>🔄 Ce qui a changé depuis le briefing du ' + summ.get("prev_issued", "précédent") + '</b><div style="margin-top:4px">' + com.get("changes", "") + '</div>' + (f'<ul style="margin:6px 0 0 18px;padding:0;font-size:12px;color:#6b5a2e">{auto}</ul>' if auto else "") + '</div>')
    # cartes des 3 jours
    H.append('<table cellpadding="0" cellspacing="4" style="width:100%;border-collapse:separate;margin:8px 0"><tr>')
    for day, (lab, a, b, prog) in TRIP.items():
        r, c = rows.get(day), com["trip"].get(day)
        if not r or not c:
            H.append(f'<td style="background:#b8c4d0;color:#fff;border-radius:12px;padding:10px 6px;text-align:center;width:33%"><div style="font-size:26px">❔</div><div style="font-weight:700">{lab}</div><div style="font-size:11px">hors de portée des modèles</div></td>'); continue
        e, col = MOOD.get(c[0], MOOD["cloud"])
        H.append(f'<td style="background:{col};color:#fff;border-radius:12px;padding:10px 6px;text-align:center;width:33%;vertical-align:top"><div style="font-size:28px">{e}</div><div style="font-weight:800;font-size:14px">{lab}</div><div style="font-size:12px;margin:2px 0">{c[1]}</div><div style="font-size:12px;font-weight:700;background:rgba(255,255,255,.22);border-radius:10px;display:inline-block;padding:1px 8px">{c[2]}</div><div style="font-size:16px;font-weight:800;margin-top:4px">{f(r["tmin"])} → {f(r["tmax"])}°</div><div style="font-size:11px;opacity:.9">pluie {a}-{b}h : {r["pwin"]} %<br>confiance {confidence(r["lead"])}</div></td>')
    H.append('</tr></table>')
    # détail par jour
    for day, (lab, a, b, prog) in TRIP.items():
        r, c = rows.get(day), com["trip"].get(day)
        if not r: continue
        H.append(f'<div style="{box}"><div style="background:#1A3A5C;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">{lab} · {prog}<span style="font-weight:400;font-size:12px;opacity:.85"> · J+{r["lead"]}</span></div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">')
        cum = "0 mm" if r["p90"] < .2 else f'{f(r["med"])} mm <span style="font-size:11px;color:#5a6b7c">(jusqu\'à {r["p90"]:.0f} mm)</span>'
        H.append(f'<tr><td {tdl}>🌧️ <b>Pluie</b></td><td {tdl}>créneau {a}-{b}h {pill(str(r["pwin"]) + " %", r["pwin"])} · journée {pill(str(r["p1"]) + " %", r["p1"])} · cumul {cum}<div style="font-size:11.5px;color:#5a6b7c;margin-top:2px">' + " · ".join(f"{k} {v} %" for k, v in r["blocks"].items() if v is not None) + '</div></td></tr>')
        H.append(f'<tr><td {tdl}>🏠 <b>Au gîte</b></td><td {tdl}>nuit {f(r["tmin"])}°' + (' <b style="color:#2f6ea0">gelée possible</b>' if r["frost"] is not None and r["frost"] <= 0 else "") + f', après-midi {f(r["tmax"])}° · rafales {f(r["g_gust"])} km/h · nuages bas {f(r["g_low"])} %</td></tr>')
        feel = r["s_feel"]
        H.append(f'<tr><td {tdl}>⛰️ <b>Crêtes</b></td><td {tdl}>{f(r["s_tmin"])} à {f(r["s_tmax"])}°, ressenti <b>{f(feel)}°</b> · vent {f(r["s_wind"])} km/h, rafales {pill(f(r["s_gust"]) + " km/h", r["s_gust"], 45, 70)} · nuages bas {pill(f(r["s_low"]) + " %", r["s_low"], 40, 70)}' + (f' · neige {f(r["snow"])} cm' if r["snow"] else "") + f'<div style="font-size:11.5px;color:#5a6b7c;margin-top:2px">iso 0° mini {f(r["iso0"])} m · lever {r.get("sunrise", "?")}, coucher {r.get("sunset", "?")}</div></td></tr>')
        if c and len(c) > 3:
            H.append(f'<tr><td colspan="2" style="padding:8px 12px;border-top:1px solid #eef2f6;background:#f6f9fc;font-size:13px">{c[3]}</td></tr>')
        H.append('</table></div>')
    # évolution des prévisions
    past = hist[-5:] + [summ]
    if len(past) > 1:
        H.append(f'<div style="{box}"><div style="background:#6b7d8f;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">📈 Évolution des prévisions d\'un briefing à l\'autre</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse"><tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th>' + "".join(f'<th {th}>{p["issued"][:5]}</th>' for p in past) + '</tr>')
        for day, (lab, a, b, _) in TRIP.items():
            cells = []
            for p in past:
                x = {q["day"]: q for q in p["rows"]}.get(day)
                cells.append(f'<td {td}>' + (f'{pill(str(x["pwin"]) + " %", x["pwin"])}<div style="font-size:11px;color:#5a6b7c">{f(x["tmax"])}° · {f(x.get("s_gust"))} km/h</div>' if x and x.get("pwin") is not None else '<span style="color:#b8c4d0">·</span>') + '</td>')
            H.append(f'<tr><td {tdl}><b>{lab}</b></td>' + "".join(cells) + '</tr>')
        H.append('</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">Pour chaque briefing : risque de pluie sur le créneau d\'activité, T maxi au gîte, rafales maxi au sommet.</div></div>')
    # d'ici là
    before = [r for r in summ["rows"] if r["day"] not in TRIP]
    if before:
        H.append(f'<div style="{box}"><div style="background:#8aa4bd;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">🥾 D\'ici là : l\'état des sentiers</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse"><tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th><th {th}>RISQUE ≥ 1 mm</th><th {th}>CUMUL</th><th {th}>T°</th></tr>')
        for r in before:
            dd = datetime.date.fromisoformat(r["day"])
            H.append(f'<tr><td {tdl}>{JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d}</td><td {td}>{pill(str(r["p1"]) + " %", r["p1"])}</td><td {td}>{f(r["med"])} mm</td><td {td}>{f(r["tmin"])} à {f(r["tmax"])}°</td></tr>')
        tot = sum(r["med"] for r in before[-4:])
        H.append(f'</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">Au gîte (1 240 m). Cumul médian des 4 derniers jours avant l\'arrivée : environ {f(round(tot, 1))} mm.</div></div>')
    H.append('<div style="background:#eef1f5;border-left:5px solid #8aa4bd;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>⚖️ Accord des modèles et fiabilité</b><div style="margin-top:4px">' + com["agreement"] + '</div></div>')
    H.append('<div style="background:#eef7ee;border-left:5px solid #1b7a34;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>🎒 Conseils pratiques</b><ul style="margin:6px 0 0 18px;padding:0">' + "".join(f"<li>{t}</li>" for t in com["tips"]) + '</ul></div>')
    H.append('<div style="font-size:11px;color:#8a99a8;text-align:center;margin:14px 0 4px">Données Open-Meteo · analyse Claude Code · <a href="https://github.com/FredericVCT/trip-moto-septembre-2026/tree/claude/meteo-buron-octobre-2026/meteo-buron" style="color:#8a99a8">sources et scripts</a></div></div>')
    open(os.path.join(HERE, "email.html"), "w").write("\n".join(H))
    print("email.html écrit")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary": summary()
    elif cmd == "render": render()
    elif cmd == "mark-sent":
        s = os.path.join(HERE, "summary.json"); h = os.path.join(HERE, "history.json")
        shutil.copy(s, os.path.join(HERE, "sent.json"))
        hist = json.load(open(h)) if os.path.exists(h) else []
        hist.append(json.load(open(s))); json.dump(hist, open(h, "w"), ensure_ascii=False, indent=1)
        print("sent.json et history.json mis à jour")
