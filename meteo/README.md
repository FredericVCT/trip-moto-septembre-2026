# Météo du trip

Chaque soir : à 18h15 l'action GitHub `meteo-fetch.yml` récupère Open-Meteo et pousse `data.json` + `hourly.txt` (le bac à sable Claude n'a pas accès à Open-Meteo) ; à 19h la routine Claude Code cloud rédige `comments.json`, rend la page, le mail et le PDF, pousse, puis envoie le mail à Frédéric. `meteo-render.yml` est un secours manuel.

- Page web : https://fredericvct.github.io/trip-moto-septembre-2026/meteo/
- PDF : https://fredericvct.github.io/trip-moto-septembre-2026/meteo/Meteo_Trip.pdf
- `build_meteo.py` : récupère Open-Meteo (ECMWF, Météo-France, ICON, GFS), produit `data.json`, puis rend `index.html`, `email.html` et le PDF à partir de `comments.json` (analyse rédigée par l'assistant).

- `data_sent.json` : copie des données du dernier briefing envoyé ; `build_meteo.py diff` liste les écarts significatifs (2°, 20 points ou 1 mm de pluie, 10 km/h de rafales) qui apparaissent dans le bloc « Ce qui a changé » du mail et du PDF.
