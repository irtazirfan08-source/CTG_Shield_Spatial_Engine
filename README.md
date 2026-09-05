# 🛡️ CTG Shield — Spatial Backend Engine

High-performance FastAPI, PostgreSQL, and PostGIS backend engine providing real-time spatial analysis, citizen authentication, and WebSocket emergency broadcasting for the Chittagong metropolitan area.

* **Production API:** https://ctg-shield-backend.onrender.com
* **Interactive Swagger Docs:** https://ctg-shield-backend.onrender.com/docs

---

## 📱 Mobile Client (Android)

Download the verified production APK featuring citizen authentication, live safety radar, and emergency SOS dispatch:

[![Download Android APK](https://img.shields.io/badge/Download-Android%20APK%20(v1.0.1)-3B82F6?style=for-the-badge&logo=android&logoColor=white)](https://github.com/irtazirfan08-source/CTG_Shield_Mobile/releases/download/v1.0.1/app-release.apk)

* **Mobile Source Repository:** [CTG_Shield_Mobile](https://github.com/irtazirfan08-source/CTG_Shield_Mobile)

---

## 🏛️ System Architecture

* **Spatial Polygon Engine:** PostgreSQL 16 + PostGIS for point-in-polygon (`ST_Contains`) and metric distance calculations (`ST_DWithin`).
* **Temporal Risk Windows:** Slices crime probabilities by recurring hour blocks (e.g., Early Morning Snatching vs. Late Night Corridors).
* **Citizen Authentication:** Direct bcrypt password hashing with Jose JWT token generation and persistent session validation.
* **Proximity SOS Dispatcher:** Asynchronous WebSocket engine tracking live client coordinates and broadcasting high-priority emergency sirens to responders within a 2.5 km radius.
* **Interactive UI:** OpenStreetMap + Leaflet.js real-time risk heatmaps and live incident reporting console.

---

## 🚀 Endpoints & Interfaces

### Authentication & Database
* `POST /api/v1/auth/register` — Citizen registration with encrypted password storage.
* `POST /api/v1/auth/login` — JWT authentication and session token issuance.
* `GET /init-db` — PostgreSQL database schema and table initialization.

### Spatial Radar & Dispatch
* `GET /map` — Interactive Chittagong high-alert polygon heatmap and incident pinboard.
* `GET /simulator` — Multi-client WebSocket proximity SOS alarm simulator.
* `GET /api/v1/safety/evaluate-location` — Evaluates real-time danger scores based on GPS coordinates and time.
* `POST /api/v1/incidents/report` — Submits crowdsourced incidents tagged with PostGIS Point geometry.
* `POST /api/v1/sos/trigger` — Broadcasts panic alerts to active responders within radius.

---

## 🛠️ Local Setup

```bash
git clone [https://github.com/irtazirfan08-source/CTG_Shield_Spatial_Engine.git](https://github.com/irtazirfan08-source/CTG_Shield_Spatial_Engine.git)
cd CTG_Shield_Spatial_Engine
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000