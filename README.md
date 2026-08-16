# CTG Shield: Real-Time Urban Safety & Spatial Proximity SOS Engine

An asynchronous geospatial crime-zone intelligence and real-time proximity panic alarm system engineered for Chittagong, Bangladesh. Built with FastAPI, PostgreSQL 16 / PostGIS spatial extensions, Leaflet.js, and bidirectional WebSockets.

---

## 🏛️ System Architecture

- **Spatial Polygon Engine:** PostgreSQL 16 + PostGIS for point-in-polygon (`ST_Contains`) and metric distance calculations (`ST_DWithin`).
- **Temporal Risk Windows:** Slices crime probabilities by recurring hour blocks (e.g., Early Morning Snatching vs. Late Night Corridors).
- **Proximity SOS Dispatcher:** Asynchronous WebSocket engine tracking live client coordinates and broadcasting high-priority emergency sirens to responders within a 2.5 km danger radius.
- **Interactive UI:** OpenStreetMap + Leaflet.js real-time risk heatmaps and live incident reporting console.

---

## 🚀 Endpoints & Interfaces

- `GET /map` — Interactive Chittagong high-alert polygon heatmap and incident pinboard.
- `GET /simulator` — Multi-client WebSocket proximity SOS alarm simulator.
- `GET /api/v1/safety/evaluate-location` — Evaluates real-time danger scores based on user GPS and time of day.
- `POST /api/v1/incidents/report` — Submits crowdsourced incidents tagged with PostGIS Point geometry.
- `POST /api/v1/sos/trigger` — Broadcasts panic alerts to active responders within radius.
- ## 📱 Mobile Application (Android)
Download the latest standalone APK build to test on any Android device:

[![Download Android APK](https://img.shields.io/badge/Download-APK%20(v1.0.0)-green?logo=android&logoColor=white)](https://github.com/irtazirfan08-source/CTG_Shield_Spatial_Engine/releases/latest)
