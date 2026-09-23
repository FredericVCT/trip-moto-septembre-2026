# Météo maison, pluie à Saint-Cyr-la-Roche

Chaque soir à 19h (Paris), une routine Claude Code cloud :
1. écrit l'heure dans `meteo-maison/trigger` et pousse sur la branche `claude/precipitation-forecast-analysis-dctml0`, ce qui lance l'action `meteo-maison.yml` (le bac à sable Claude n'a pas accès à Open-Meteo) ;
2. attend le commit « Météo maison : données du ... » qui met à jour `raw.json` (10 modèles déterministes + ensembles ECMWF IFS, ECMWF AIFS, ICON, GFS) ;
3. lance `build_email.py summary`, rédige `comments.json`, lance `build_email.py render` ;
4. envoie `email.html` par Gmail à fvincenot@gmail.com, puis `build_email.py mark-sent` et pousse.

- `fetch_pluie.py` : récupération Open-Meteo (exécuté par l'action GitHub).
- `build_email.py` : calcul des probabilités, comparaison avec le dernier briefing (`sent.json`) et rendu du mail. Format de `comments.json` dans l'en-tête du script.
