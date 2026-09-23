#!/usr/bin/env python3
"""Rend meteo-maison/email.html à partir de raw.json et des commentaires ci-dessous."""
import json, os, statistics as st, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "raw.json")))
T = d["det"]["ecmwf_ifs025"]["hourly"]["time"]
JOURS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
LAB = {"arome_france": "AROME", "meteofrance_seamless": "Météo-France", "ecmwf_ifs025": "ECMWF", "ecmwf_aifs025_single": "AIFS",
       "icon_seamless": "ICON", "gfs_seamless": "GFS", "ukmo_seamless": "UKMO"}
COM = {
 "2026-09-23": ("sun", "Grand beau, chaud", "Sec garanti"),
 "2026-09-24": ("hot", "Grand beau, très chaud", "Sec garanti"),
 "2026-09-25": ("hot", "Grand beau, pic de chaleur", "Sec garanti"),
 "2026-09-26": ("sun", "Beau, un peu plus frais", "Sec"),
 "2026-09-27": ("cloud", "Sec la journée, pluie le soir", "Rentrer avant 18h"),
 "2026-09-28": ("rain", "Journée pluvieuse, surtout le matin", "À éviter"),
 "2026-09-29": ("wind", "Averses éparses et vent", "Incertain"),
 "2026-09-30": ("rain", "Nouveau passage pluvieux l'après-midi", "Pluie probable"),
 "2026-10-01": ("rain", "Instable et nettement plus frais", "Pluie probable"),
 "2026-10-02": ("cloud", "Frais, accalmie possible", "Tendance"),
}
MOOD = {"sun": ("☀️", "#f2a516"), "hot": ("🌞", "#e9821b"), "rain": ("🌧️", "#6b7d8f"), "cloud": ("⛅", "#8aa4bd"), "wind": ("💨", "#7a8fa6")}
def pill(txt, p):
    bg, fg = ("#e2f5e6", "#1b7a34") if p < 20 else (("#fff1cf", "#9a6300") if p < 50 else ("#ffe0e0", "#b52323"))
    return f'<span style="display:inline-block;border-radius:20px;padding:2px 9px;font-weight:700;font-size:12px;background:{bg};color:{fg};white-space:nowrap">{txt}</span>'
def daysum(arr, day, a=0, b=24):
    v = [x for t, x in zip(T, arr) if t[:10] == day and a <= int(t[11:13]) < b and x is not None]
    return sum(v) if len(v) == b - a else None
rows = []
for day in sorted(COM):
    tots, blocks = [], {n: [] for n in ("nuit", "matin", "après-midi", "soir")}
    for m, v in d["ens"].items():
        h = v["hourly"]
        for k in h:
            if not k.startswith("precipitation") or m == "meteofrance_arpege_world": continue
            s = daysum(h[k], day)
            if s is not None: tots.append(s)
            for (a, b), n in zip(((0, 6), (6, 12), (12, 18), (18, 24)), blocks):
                s = daysum(h[k], day, a, b)
                if s is not None: blocks[n].append(s)
    p1 = round(100 * sum(x >= 1 for x in tots) / len(tots)); s = sorted(tots)
    med, p90 = st.median(tots), s[int(.9 * (len(s) - 1))]
    bl = {n: round(100 * sum(x >= .5 for x in v) / len(v)) for n, v in blocks.items() if v}
    det = []
    for m, lab in LAB.items():
        x = daysum(d["det"][m]["hourly"]["precipitation"], day)
        if x is not None: det.append(f"{lab} {x:.1f}".replace(".", ","))
    h = d["det"]["ecmwf_ifs025"]["hourly"]
    tt = [x for t, x in zip(T, h["temperature_2m"]) if t[:10] == day]
    g = max(x for t, x in zip(T, h["wind_gusts_10m"]) if t[:10] == day and x is not None)
    rows.append(dict(day=day, p1=p1, med=med, p90=p90, bl=bl, det=det, tmin=min(tt), tmax=max(tt), gust=g, n=len(tots)))
f = lambda x: f"{x:.1f}".replace(".", ",")
issued = datetime.datetime.strptime(d["issued_utc"], "%Y-%m-%d %H:%M") + datetime.timedelta(hours=2)
H = []
H.append('<div style="font-family:-apple-system,\'Helvetica Neue\',Arial,sans-serif;max-width:720px;margin:0 auto;color:#1b2733;font-size:13.5px">')
H.append(f'<div style="background:#1A3A5C;color:#fff;border-radius:14px;padding:16px 20px"><div style="font-size:24px;font-weight:800">🌧️ Météo maison · Saint-Cyr-la-Roche</div><div style="opacity:.9;font-size:13px;margin-top:4px">Point du {issued:%d/%m/%Y %H:%M} · 10 modèles (AROME, Météo-France, ECMWF IFS et AIFS, ICON, GFS, UKMO) + 173 scénarios d\'ensemble</div></div>')
H.append('<div style="background:#eef4fa;border-left:5px solid #2f6ea0;border-radius:8px;padding:10px 14px;margin:12px 0;font-size:14px"><b>En résumé :</b> sec garanti jusqu\'à samedi 26 inclus, avec la fin de l\'épisode de chaleur (jusqu\'à 32° vendredi). La pluie arrive dimanche soir, et <b>lundi 28 est le jour le plus arrosé</b> : environ 6 chances sur 10 de dépasser 1 mm, surtout la nuit et le matin. La semaine prochaine reste humide, avec un deuxième passage pluvieux mercredi 30 et jeudi 1er, et un net rafraîchissement (maxi 17° jeudi).</div>')
H.append('<div style="background:#fff8e6;border-left:5px solid #e9a21b;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>⚖️ Accord des modèles</b><div style="margin-top:4px">Unanimité sur le sec jusqu\'à samedi : les 10 modèles et les 173 scénarios donnent 0 mm. Pour lundi, tous voient arriver la pluie mais pas en même quantité : ECMWF annonce 27 mm, GFS 12 mm, alors que l\'AIFS (IA d\'ECMWF) et ICON restent presque secs. Au-delà de mardi, ce sont des tendances, pas des horaires.</div></div>')
H.append('<table cellpadding="0" cellspacing="4" style="width:100%;border-collapse:separate;margin:8px 0"><tr>')
for r in rows[:5]:
    dd = datetime.date.fromisoformat(r["day"]); e, c = MOOD[COM[r["day"]][0]]
    H.append(f'<td style="background:{c};color:#fff;border-radius:12px;padding:8px 4px;text-align:center;width:20%"><div style="font-size:26px">{e}</div><div style="font-weight:700;font-size:13px">{JOURS[dd.weekday()]} {dd.day}</div><div style="font-size:11px">{COM[r["day"]][2]}</div><div style="font-size:15px;font-weight:800">{r["tmin"]:.0f} → {r["tmax"]:.0f}°</div></td>')
H.append('</tr><tr>')
for r in rows[5:]:
    dd = datetime.date.fromisoformat(r["day"]); e, c = MOOD[COM[r["day"]][0]]
    H.append(f'<td style="background:{c};color:#fff;border-radius:12px;padding:8px 4px;text-align:center;width:20%"><div style="font-size:26px">{e}</div><div style="font-weight:700;font-size:13px">{JOURS[dd.weekday()]} {dd.day}</div><div style="font-size:11px">{COM[r["day"]][2]}</div><div style="font-size:15px;font-weight:800">{r["tmin"]:.0f} → {r["tmax"]:.0f}°</div></td>')
H.append('</tr></table>')
th = 'style="font-size:11px;color:#5a6b7c;padding:6px 4px 2px"'
H.append(f'<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#1A3A5C;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">📅 Jour par jour</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse"><tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th><th {th}>🌡️ TEMP.</th><th {th}>🌧️ RISQUE ≥ 1 mm</th><th {th}>CUMUL</th><th {th}>💨 RAF.</th></tr>')
td = 'style="padding:6px 4px;border-top:1px solid #eef2f6;text-align:center;white-space:nowrap"'
for r in rows:
    dd = datetime.date.fromisoformat(r["day"])
    cum = "0 mm" if r["p90"] < .2 else f'{f(r["med"])} mm <span style="font-size:11px;color:#5a6b7c">(jusqu\'à {r["p90"]:.0f})</span>'
    H.append(f'<tr><td style="padding:6px 10px;border-top:1px solid #eef2f6"><b>{JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d}</b><div style="font-size:11.5px;color:#5a6b7c">{COM[r["day"]][1]}</div></td><td {td}><b>{r["tmin"]:.0f} à {r["tmax"]:.0f}°</b></td><td {td}>{pill(str(r["p1"]) + " %", r["p1"])}</td><td {td}>{cum}</td><td {td}>{r["gust"]:.0f} km/h</td></tr>')
H.append('</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">Risque : part des 173 scénarios d\'ensemble (ECMWF, AIFS, ICON, GFS) qui donnent au moins 1 mm dans la journée. Cumul : valeur médiane, et entre parenthèses le cumul atteint dans les 10 % de scénarios les plus pluvieux.</div></div>')
H.append('<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#6b7d8f;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">⏰ Quand pleut-il ? Risque d\'au moins 0,5 mm par tranche de 6 h</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">')
H.append(f'<tr><th style="text-align:left;font-size:11px;color:#5a6b7c;padding:6px 10px 2px">JOUR</th><th {th}>NUIT 0-6h</th><th {th}>MATIN 6-12h</th><th {th}>APRÈS-MIDI 12-18h</th><th {th}>SOIR 18-24h</th></tr>')
for r in rows[3:9]:
    dd = datetime.date.fromisoformat(r["day"])
    H.append(f'<tr><td style="padding:6px 10px;border-top:1px solid #eef2f6;font-weight:600">{JOURS[dd.weekday()]} {dd.day:02d}/{dd.month:02d}</td>' + "".join(f'<td {td}>{pill(str(v) + " %", v)}</td>' for v in r["bl"].values()) + "</tr>")
H.append('</table></div>')
H.append('<div style="border:2px solid #dde5ee;border-radius:14px;margin:10px 0;overflow:hidden"><div style="background:#8aa4bd;color:#fff;padding:9px 14px;font-weight:800;font-size:15px">🔬 Détail des modèles (cumul du jour en mm)</div><table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse">')
for r in rows[3:]:
    dd = datetime.date.fromisoformat(r["day"])
    H.append(f'<tr><td style="padding:5px 10px;border-top:1px solid #eef2f6;font-weight:600;white-space:nowrap">{JOURS[dd.weekday()]} {dd.day:02d}</td><td style="padding:5px 10px;border-top:1px solid #eef2f6;font-size:12px">{" · ".join(r["det"])}</td></tr>')
H.append('</table><div style="font-size:11px;color:#5a6b7c;padding:6px 10px 8px">AROME couvre 2 jours, Météo-France 4, ICON et UKMO 7, ECMWF et GFS 10.</div></div>')
H.append('<div style="background:#eef7ee;border-left:5px solid #1b7a34;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13px"><b>🧰 Conseils pratiques</b><ul style="margin:6px 0 0 18px;padding:0">'
         '<li>Sorties moto, tonte, travaux extérieurs : profitez de jeudi à samedi, et de dimanche jusqu\'en fin d\'après-midi.</li>'
         '<li>Lundi 28 : journée à éviter pour la moto, surtout le matin. Dans le pire des cas (1 scénario sur 10), plus de 20 mm.</li>'
         '<li>Arrosage : inutile de prévoir un gros arrosage pour la semaine prochaine, la pluie devrait prendre le relais dès dimanche soir.</li>'
         '<li>Fin de semaine prochaine : on passe de 32° à 17° en une semaine, ressortir les vêtements de mi-saison.</li></ul></div>')
H.append('<div style="font-size:11px;color:#8a99a8;text-align:center;margin:14px 0 4px">Données Open-Meteo · analyse Claude Code · <a href="https://github.com/FredericVCT/trip-moto-septembre-2026/tree/claude/precipitation-forecast-analysis-dctml0/meteo-maison" style="color:#8a99a8">sources et scripts</a></div></div>')
open(os.path.join(HERE, "email.html"), "w").write("\n".join(H))
for r in rows: print(r["day"], r["p1"], round(r["med"], 1), r["p90"], r["bl"])
