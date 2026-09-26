#!/usr/bin/env python3
"""Briefing pluie Saint-Cyr-la-Roche.

Usage :
  python3 build_email.py summary    -> calcule meteo-maison/summary.json à partir de raw.json, l'affiche,
                                        et liste les écarts avec sent.json (dernier briefing envoyé)
  python3 build_email.py render     -> meteo-maison/email.html à partir de summary.json + comments.json
  python3 build_email.py mark-sent  -> copie summary.json vers sent.json (après l'envoi du mail)

Orages : `storm` = part des scénarios d'ensemble dotés du CAPE (énergie convective) où une même heure
combine CAPE >= 800 J/kg et pluie >= 0,5 mm ; `tsm` = modèles déterministes prévoyant de l'orage
(weather_code 95 à 99) avec les heures ; `cape` = CAPE maximal du jour (ECMWF, sinon GFS).

comments.json (rédigé par l'assistant après lecture de `summary`) :
{
  "headline": "synthèse (HTML léger)",
  "agreement": "accord ou désaccord des modèles (HTML léger)",
  "changes": "ce qui a changé depuis le dernier briefing (vide s'il n'y en a pas)",
  "days": {"2026-09-23": ["sun|hot|rain|cloud|wind|storm", "libellé court", "badge 1 à 3 mots"], ...},
  (mood « storm » dès que le risque d'orage est >= 30 % ou que 2 modèles prévoient de l'orage)
  "tips": ["conseil 1", "conseil 2", ...]
}
"""
import json, os, sys, shutil, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "raw.json")))
T = d["det"]["ecmwf_ifs025"]["hourly"]["time"]
JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
LAB = {"arome_france": "AROME", "meteofrance_seamless": "Météo-France", "ecmwf_ifs025": "ECMWF", "ecmwf_aifs025_single": "AIFS",
       "icon_seamless": "ICON", "gfs_seamless": "GFS", "ukmo_seamless": "UKMO"}
MOOD = {"storm": ("⛈️", "#5a6b7c"), "sun": ("☀️", "#f2a516"), "hot": ("🌞", "#e9821b"), "rain": ("🌧️", "#6b7d8f"), "cloud": ("⛅", "#8aa4bd"), "wind": ("💨", "#7a8fa6")}
def pill(txt, p):
    bg, fg = ("#e2f5e6", "#1b7a34") if p < 20 else (("#fff1cf", "#9a6300") if p < 50 else ("#ffe0e0", "#b52323"))
    return f'<span style="display:inline-block;border-radius:20px;padding:2px 9px;font-weight:700;font-size:12px;background:{bg};color:{fg};white-space:nowrap">{txt}</span>'
def orage(r):
    p = r.get("storm")
    if p is None and not r.get("tsm"): return '<span style="color:#8a99a8">n.d.</span>'
    p = p or 0
    if r.get("tsm"): p = max(p, 20)  # au moins « à surveiller » si un modèle prévoit de l'orage
    return pill(("⚡ " if p >= 20 else "") + str(p) + " %", p)
def daysum(arr, day, a=0, b=24):
    v = [x for t, x in zip(T, arr) if t[:10] == day and a <= int(t[11:13]) < b and x is not None]
    return sum(v) if len(v) == b - a else None
def compute():
    rows = []
    today = datetime.datetime.strptime(issued_local(), "%d/%m/%Y %H:%M").date().isoformat()
    for day in sorted(set(t[:10] for t in T)):
        if day <= today: continue  # le briefing du soir commence à demain
        tots, blocks, stm = [], {n: [] for n in ("nuit", "matin", "après-midi", "soir")}, []
        for m, v in d["ens"].items():
            h = v["hourly"]
            for k in h:
                if not k.startswith("precipitation") or m == "meteofrance_arpege_world": continue
                s = daysum(h[k], day)
                if s is not None: tots.append(s)
                ck = k.replace("precipitation", "cape")
                if ck in h:
                    pairs = [(p, c) for t, p, c in zip(T, h[k], h[ck]) if t[:10] == day and p is not None and c is not None]
                    if len(pairs) >= 20: stm.append(any(p >= .5 and c >= 800 for p, c in pairs))
                for (a, b), n in zip(((0, 6), (6, 12), (12, 18), (18, 24)), blocks):
                    s = daysum(h[k], day, a, b)
                    if s is not None: blocks[n].append(s)
        if not tots: continue
        p1 = round(100 * sum(x >= 1 for x in tots) / len(tots)); s = sorted(tots)
        med, p90 = st.median(tots), s[int(.9 * (len(s) - 1))]
        bl = {n: round(100 * sum(x >= .5 for x in v) / len(v)) for n, v in blocks.items() if v}
        det = []
        for m, lab in LAB.items():
            x = daysum(d["det"][m]["hourly"]["precipitation"], day)
            if x is not None: det.append(f"{lab} {x:.1f}".replace(".", ","))
        tsm = []
        for m, lab in LAB.items():
            hm = d["det"][m]["hourly"]
            hrs = [int(t[11:13]) for t, w in zip(T, hm.get("weather_code", [])) if t[:10] == day and w is not None and w >= 95]
            if hrs: tsm.append(f"{lab} {min(hrs)}h-{max(hrs) + 1}h")
        cape = None
        for m in ("ecmwf_ifs025", "gfs_seamless"):
            cv = [x for t, x in zip(T, d["det"][m]["hourly"].get("cape", [])) if t[:10] == day and x is not None]
            if cv: cape = round(max(cv)); break
        storm = round(100 * sum(stm) / len(stm)) if stm else None
        h = d["det"]["ecmwf_ifs025"]["hourly"]
        tt = [x for t, x in zip(T, h["temperature_2m"]) if t[:10] == day]
        g = max(x for t, x in zip(T, h["wind_gusts_10m"]) if t[:10] == day and x is not None)
        rows.append(dict(day=day, p1=p1, med=round(med, 1), p90=round(p90, 1), bl=bl, det=det, tmin=round(min(tt)), tmax=round(max(tt)), gust=round(g), n=len(tots), storm=storm, tsm=tsm, cape=cape))
    return rows

def render():
    summ = json.load(open(os.path.join(HERE, "summary.json")))
    com = json.load(open(os.path.join(HERE, "comments.json")))
    rows, C = summ["rows"], com["days"]
    f = lambda x: f"{x:.1f}".replace(".", ",")
    H = []
    H.append('<div style="font-family:-apple-system,\'Helvetica Neue\',Arial,sans-serif;max-width:720px;margin:0 auto;color:#1b2733;font-size:13.5px">')
    H.append(f'<div style="background:#1A3A5C;color:#fff;border-radius:14px;padding:16px 20px"><div style="font-size:24px;font-weight:800">🌧️ Météo maison · Saint-Cyr-la-Roche</div><div style="opacity:.9;font-size:13px;margin-top:4px">Point du {summ["issued"]} · 10 modèles (AROME, Météo-France, ECMWF IFS et AIFS, ICON, GFS, UKMO) + {rows[0]["n"]} scénarios d\'ensemble</div></div>')
    H.append('<div style="background:#eef4fa;border-left:5px solid #2f6ea0;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px"><b>En résumé :</b> ' + com["headline"] + '</div>')
    if com.get("changes"):
        H.append('<div style="background:#fff8e6;border-left:5px solid #e9a21b;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>🔄 Ce qui a changé depuis le briefing du ' + summ.get("prev_issued", "précédent") + '</b><div style="margin-top:4px">' + com["changes"] + '</div></div>')
    H.append('<div style="background:#eef1f5;border-left:5px solid #8aa4bd;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>⚖️ Accord des modèles</b><div style="margin-top:4px">' + com["agreement"] + '</div></div>')
    H.append('<table cellpadding="0" cellspacing="4" style="width:100%;border-collapse:separate;margin:8px 0"><tr>')
    for r in rows[:5]:
        dd = datetime.date.fromisoformat(r["day"]); e, c = MOOD[C[r["day"]][0]]
        H.append(f'<td style="background:{c};color:#fff;border-radius:12px;padding:8px 4px;text-align:center;width:20%"><div style="font-size:26px">{e}</div><div style="font-weight:700;font-size:13px">{JOURS[dd.weekday()]} {dd.day}</div><div style="font-size:11px">{C[r["day"]][2]}</div><div style="font-size:15px;font-weight:800">{r["tmin"]:.0f} → {r["tmax"]:.0f}°</div></td>')
    H.append('</tr><tr>')
    for r in rows[5:]:
        dd = datetime.date.fromisoformat(r["day"]); e, c = MOOD[C[r["day"]][0]]
        H.append(f'<td style="background:{c};color:#fff;border-radius:12px;padding:8px 4px;text-align:center;width:20%"><div style="font-size:26px">{e}</div><div style="font-weight:700;font-size:13px">{JOURS[dd.weekday()]} {dd.day}</div><div style="font-size:11px">{C[r["day"]][2]}</div><div style="font-size:15px;font-weight:800">{r["tmin"]:.0f} → {r["tmax"]:.0f}°</div></td>')
    H.append('</tr></table>')
    th = 'style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px"'
    H.append(f'<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#1A3A5C;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">📅 Jour par jour</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse"><tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th><th {th}>🌡️ TEMP.</th><th {th}>🌧️ RISQUE ≥ 1 mm</th><th {th}>CUMUL</th><th {th}>⚡ ORAGE</th><th {th}>💨 RAF.</th></tr>')
    td = 'style="padding:6px 4px;border-top:1px solid #eef2f6;text-align:center;white-space:nowrap"'
    for r in rows:
        dd = datetime.date.fromisoformat(r["day"])
        cum = "0 mm" if r["p90"] < .2 else f'{f(r["med"])} mm <span style="font-size:11px;color:#5a6b7c">(jusqu\'à {r["p90"]:.0f})</span>'
        H.append(f'<tr><td style="padding:6px 10px;border-top:1px solid #eef2f6"><b>{JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d}</b><div style="font-size:11.5px;color:#5a6b7c">{C[r["day"]][1]}</div></td><td {td}><b>{r["tmin"]:.0f} à {r["tmax"]:.0f}°</b></td><td {td}>{pill(str(r["p1"]) + " %", r["p1"])}</td><td {td}>{cum}</td><td {td}>{orage(r)}</td><td {td}>{r["gust"]:.0f} km/h</td></tr>')
    H.append('</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">Risque : part des scénarios d\'ensemble (ECMWF, AIFS, ICON, GFS) qui donnent au moins 1 mm dans la journée. Cumul : valeur médiane, et entre parenthèses le cumul atteint dans les 10 % de scénarios les plus pluvieux. Orage : part des scénarios où une même heure combine forte énergie convective (CAPE ≥ 800 J/kg) et pluie, relevée à 20 % au moins si un modèle prévoit explicitement de l\'orage.</div></div>')
    H.append('<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#6b7d8f;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">⏰ Quand pleut-il ? Risque d\'au moins 0,5 mm par tranche de 6 h</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">')
    H.append(f'<tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th><th {th}>NUIT 0-6h</th><th {th}>MATIN 6-12h</th><th {th}>APRÈS-MIDI 12-18h</th><th {th}>SOIR 18-24h</th></tr>')
    for r in rows[:7]:
        dd = datetime.date.fromisoformat(r["day"])
        H.append(f'<tr><td style="padding:6px 10px;border-top:1px solid #eef2f6;font-weight:600">{JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d}</td>' + "".join(f'<td {td}>{pill(str(v) + " %", v)}</td>' for v in r["bl"].values()) + "</tr>")
    H.append('</table></div>')
    H.append('<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#8aa4bd;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">🔬 Détail des modèles (cumul du jour en mm)</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">')
    for r in [x for x in rows if x["p90"] >= .2 or x.get("tsm")]:
        dd = datetime.date.fromisoformat(r["day"])
        H.append(f'<tr><td style="padding:5px 10px;border-top:1px solid #eef2f6;font-weight:600;white-space:nowrap">{JOURS[dd.weekday()]} {dd.day:02d}</td><td style="padding:5px 10px;border-top:1px solid #eef2f6;font-size:12px">{" · ".join(r["det"])}{(" · <b>⚡ orage : " + ", ".join(r["tsm"]) + "</b>") if r.get("tsm") else ""}</td></tr>')
    H.append('</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">AROME couvre 2 jours, Météo-France 4, ICON et UKMO 7, ECMWF et GFS 10.</div></div>')
    H.append('<div style="background:#eef7ee;border-left:5px solid #1b7a34;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>🧰 Conseils pratiques</b><ul style="margin:6px 0 0 18px;padding:0">' + "".join(f"<li>{t}</li>" for t in com["tips"]) + '</ul></div>')
    H.append('<div style="font-size:11px;color:#8a99a8;text-align:center;margin:14px 0 4px">Données Open-Meteo · analyse Claude Code · <a href="https://github.com/FredericVCT/trip-moto-septembre-2026/tree/claude/precipitation-forecast-analysis-dctml0/meteo-maison" style="color:#8a99a8">sources et scripts</a></div></div>')
    open(os.path.join(HERE, "email.html"), "w").write("\n".join(H))
    print("email.html écrit")

def issued_local():
    u = datetime.datetime.strptime(d["issued_utc"], "%Y-%m-%d %H:%M").replace(tzinfo=datetime.timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        return u.astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return (u + datetime.timedelta(hours=2)).strftime("%d/%m/%Y %H:%M")

def summary():
    rows = compute()
    out = {"issued": issued_local(), "rows": rows}
    ps = os.path.join(HERE, "sent.json")
    print(f"Données émises le {out['issued']} (heure de Paris)")
    print("jour        T°      P>=1mm  médiane  p90   rafales  orage  CAPE | nuit/matin/aprem/soir (P>=0,5mm)  | modèles (mm) | orage prévu par")
    for r in rows:
        print(f"{r['day']}  {r['tmin']:>2}/{r['tmax']:<2}°  {r['p1']:>4} %  {r['med']:>5}   {r['p90']:>5}  {r['gust']:>3} km/h  {(str(r.get('storm')) + ' %') if r.get('storm') is not None else 'n.d.':>5}  {r.get('cape') if r.get('cape') is not None else '-':>4} | " + "/".join(str(v) for v in r['bl'].values()) + " | " + " · ".join(r['det']) + " | " + (", ".join(r.get('tsm') or []) or "aucun"))
    if os.path.exists(ps):
        old = json.load(open(ps)); out["prev_issued"] = old["issued"]
        orow = {r["day"]: r for r in old["rows"]}
        lines = []
        for r in rows:
            o = orow.get(r["day"])
            if not o: continue
            parts = []
            if abs(r["p1"] - o["p1"]) >= 20: parts.append(f"risque {o['p1']} % → {r['p1']} %")
            if abs(r["med"] - o["med"]) >= 2 or abs(r["p90"] - o["p90"]) >= 5: parts.append(f"cumul {o['med']} (p90 {o['p90']}) → {r['med']} (p90 {r['p90']}) mm")
            if r.get("storm") is not None and o.get("storm") is not None and abs(r["storm"] - o["storm"]) >= 20: parts.append(f"orage {o['storm']} % → {r['storm']} %")
            if bool(r.get("tsm")) != bool(o.get("tsm")): parts.append("orage prévu par " + (", ".join(r["tsm"]) if r.get("tsm") else "plus aucun modèle"))
            if abs(r["tmax"] - o["tmax"]) >= 3: parts.append(f"T max {o['tmax']} → {r['tmax']}°")
            if parts: lines.append(f"{r['day']} : " + " ; ".join(parts))
        out["changes"] = lines
        print(f"\nÉcarts depuis le briefing du {old['issued']} (seuils : 20 pts de pluie ou d'orage, 2 mm, 3°) :")
        print("\n".join("  - " + l for l in lines) if lines else "  aucun écart notable")
    else:
        print("\nPas de briefing précédent (sent.json absent).")
    json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary": summary()
    elif cmd == "render": render()
    elif cmd == "mark-sent":
        shutil.copy(os.path.join(HERE, "summary.json"), os.path.join(HERE, "sent.json")); print("sent.json mis à jour")
