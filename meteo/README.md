# Météo du trip

Généré chaque soir (19h) par une routine Claude Code cloud, puis envoyé par mail à Frédéric.

- Page web : https://fredericvct.github.io/trip-moto-septembre-2026/meteo/
- PDF : https://fredericvct.github.io/trip-moto-septembre-2026/meteo/Meteo_Trip.pdf
- `build_meteo.py` : récupère Open-Meteo (ECMWF, Météo-France, ICON, GFS), produit `data.json`, puis rend `index.html`, `email.html` et le PDF à partir de `comments.json` (analyse rédigée par l'assistant).
