# Météo du séjour au Buron de la Tâche (Mont-Dore), 5 au 7 octobre 2026

Chaque soir à 19h15 (Paris), du 23 septembre au 6 octobre, une routine Claude Code cloud :
1. écrit l'heure dans `meteo-buron/trigger` et pousse sur la branche `claude/meteo-buron-octobre-2026`, ce qui lance l'action `meteo-buron.yml` (le bac à sable Claude n'a pas accès à Open-Meteo) ;
2. attend le commit « Météo Buron : données du ... » qui met à jour `raw.json` ;
3. lance `build_email.py summary`, rédige `comments.json`, lance `build_email.py render` ;
4. envoie `email.html` par Gmail à fvincenot@gmail.com, puis `build_email.py mark-sent` (met à jour `sent.json` et `history.json`) et pousse.

Deux points : le gîte (719 route de la Tâche, 1 240 m) et le sommet du Puy de Sancy (1 886 m, pour les crêtes).
Créneaux d'activité : lundi 5 de 14h à 20h, mardi 6 de 8h à 19h, mercredi 7 de 10h à 17h.

- `fetch_buron.py` : récupération Open-Meteo (7 modèles déterministes, ensembles ECMWF IFS, ECMWF AIFS, ICON, GFS), exécuté par l'action GitHub.
- `build_email.py` : calculs, comparaison avec le dernier briefing (`sent.json`), historique (`history.json`) et rendu du mail. Format de `comments.json` dans l'en-tête du script.
