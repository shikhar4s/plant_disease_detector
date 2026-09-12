# PLANTDOC — AI-Powered Crop Health & Market Intelligence Platform

PlantDoc combines authenticated leaf-image diagnosis history with live Indian mandi records, current farm weather, transparent weather-favourability rules, commodity watchlists and a context-aware farmer assistant.

**Developer: Shikhar Shrivastava**

PlantDoc is advisory software. A classifier result is a possible match, not a guaranteed diagnosis. Model confidence is not disease severity. Weather risk describes conditions that may favour disease; it does not prove infection. Consult a qualified agricultural expert for serious or spreading crop problems and before applying crop-protection products.

## Product features

- Private registration, login, JWT refresh, logout, editable profile and owner-isolated data.
- Drag/drop, file browsing and supported-device camera input with preview, replace/remove and an explicit **Diagnose** action.
- Crop, disease, confidence, Healthy / Possible disease / Uncertain status, symptoms, possible causes, actions, prevention and an advisory disclaimer.
- Quality checks for corrupt, oversized, extremely dark/bright and almost detail-free images. This is not a validated leaf detector.
- Saved diagnoses with compact database previews, crop, condition, status, confidence, model version, timestamp, notes, exports and detail views.
- Live AGMARKNET mandi data through data.gov.in with search, filters, sorting, pagination, modal/min/max prices, dates, source, fetch time and comparison scope.
- Snapshot-backed price-history collection. Trends remain unavailable until at least two like-for-like observations exist; the application never manufactures history.
- Open-Meteo city search and user-triggered geolocation with current conditions and a seven-day forecast.
- A separate rule-based Low / Moderate / High weather-favourability result with reasons and explicit scientific limitations.
- Database-backed commodity watchlists with owner isolation and latest stored observations.
- Gemini farmer assistant with server-owned diagnosis/weather/mandi context. Missing live context produces an explicit “live data required” response; fallback answers identify themselves as limited built-in guidance.
- English and Hindi coverage for the main platform. Existing Spanish and French authentication/history translations remain available and fall back to English for new strings.
- Direct routes such as `/dashboard/diagnose`, `/dashboard/mandi`, `/dashboard/weather`, `/dashboard/history`, `/dashboard/assistant`, `/dashboard/about` and `/dashboard/profile` survive refreshes.

## Architecture

```text
React + TypeScript + Vite
        │ authenticated JSON/multipart API
        ▼
Django REST Framework
 ├─ ML inference + versioned class registry
 ├─ conservative disease information
 ├─ AGMARKNET/data.gov.in provider + snapshot cache
 ├─ Open-Meteo provider
 ├─ transparent weather-risk rules
 ├─ bounded assistant context + Gemini REST client
 └─ PostgreSQL persistence and owner isolation
```

Production serves the compiled React application and Django API from the same Render web service. WhiteNoise serves static assets; Gunicorn uses one worker/thread to stay within the free service's 512 MiB memory limit.

## Disease model

The active artifact remains `plant_disease_detector/deployment_artifacts/plant_disease_model.pth` because the repository does not contain a labelled evaluation set, original split, duplicate groups, training log or dataset version. Replacing it with an unevaluated downloaded model would not meet the upgrade's evidence standard.

- Model version: `legacy-cnn-pv38-v1`
- Architecture: custom residual CNN, 6,594,222 state parameters
- Classes: 38 single-label crop/condition classes, including healthy classes
- Input: 256 × 256 RGB, bilinear resize, divide by 255 into `[0, 1]`
- Weights size: 26,396,688 bytes (25.17 MiB)
- SHA-256: `18451c4ba8262edbda24ef91954945d9b3da92db40f5b0a3cad9ef92b7439a86`
- Local CPU benchmark: median 1,080.33 ms, p95 1,225.71 ms over 50 post-warm-up runs with one Torch thread; observed process RSS delta 57,896,960 bytes
- Uncertainty threshold: 0.70 legacy display heuristic, **not calibrated**
- Validation/test accuracy, precision, recall, macro F1, per-class metrics and confusion matrix: **unavailable and not claimed**
- Field-image evaluation: **not performed**

See [docs/MODEL_CARD.md](docs/MODEL_CARD.md) for limitations, the candidate-architecture protocol and datasets reviewed. The machine-readable manifest is `plant_disease_detector/deployment_artifacts/model_manifest.json`; the ordered mapping is `plant_disease_detector/deployment_artifacts/class_names.json`.

## External APIs

### Mandi rates

The backend uses the Government of India Open Government Data resource “Current Daily Price of Various Commodities from Various Markets (Mandi),” generated through AGMARKNET. It returns minimum, maximum and modal wholesale price; PlantDoc never describes modal price as an arithmetic average. The source unit is displayed as INR/quintal for this resource.

`DATA_GOV_IN_API_KEY` is required. Requests use connect/read timeouts, 15-minute caching, bounded result windows, schema validation and clear provider errors. Comparisons state whether the provider total exceeded the fetched window.

### Weather

Open-Meteo provides geocoding and seven-day forecasts: temperature, feels-like temperature, humidity, precipitation, rain probability, wind, weather code and timezone. No API key is required for ordinary use, subject to current terms and traffic limits. Responses are cached for 10 minutes.

The risk rules use humidity, forecast rain/precipitation and temperature as broad weather-favourability signals. They are intentionally not crop-specific disease models. The UI cites the American Phytopathological Society's disease-triangle lesson and peer-reviewed leaf-wetness review; the numeric cutoffs remain a conservative application heuristic, not a validated forecast.

### Gemini

Gemini is optional. `GEMINI_MODEL` defaults to `gemini-3.5-flash`; `render.yaml` uses the same value so a Blueprint sync cannot restore the prior identifier. Calls use bounded content, timeouts, one bounded retry for transient capacity errors and conservative prompts. Credentials stay in Render and are never logged or committed.

## Local setup

Requirements: Python 3.12, Node.js 22 and PostgreSQL for production-like testing. SQLite is allowed only with `DEBUG=true`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r plant_disease_detector/requirements.txt
python plant_disease_detector/manage.py migrate
python plant_disease_detector/manage.py runserver
```

On Windows activate with `.venv\Scripts\activate`. In another terminal:

```bash
cd plant_disease_detector_frontend
npm ci
npm run dev
```

Vite proxies `/api` and `/healthz` to Django at `127.0.0.1:8000`.

## Environment variables

Copy the backend `.env.example` to `.env`. `.env` files are ignored; the example contains variable names with empty values only. Use the defaults described below or in `render.yaml` where appropriate.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | production | Django signing secret |
| `DEBUG` | yes | `false` in production |
| `DATABASE_URL` | production | Persistent PostgreSQL connection |
| `ALLOWED_HOSTS` | optional | Extra comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | separate frontend only | Allowed frontend origins |
| `GEMINI_API_KEY` | optional | Gemini assistant/guidance |
| `GEMINI_MODEL` | optional | Defaults to `gemini-3.5-flash` |
| `DATA_GOV_IN_API_KEY` | mandi required | data.gov.in API key |
| `DATA_GOV_IN_RESOURCE_ID` | optional | Current mandi resource ID |
| `MANDI_FETCH_LIMIT` | optional | Upstream window, default 1000, max 2000 |
| `OMP_NUM_THREADS` | hosted | Bound Torch CPU use |
| `MALLOC_ARENA_MAX` | hosted | Bound allocator arenas |

The frontend accepts only `VITE_API_BASE_URL`, normally blank for the combined deployment.

## Storage and database design

PostgreSQL stores users, diagnosis metadata, notes, model version, compressed JPEG preview bytes, mandi snapshots and watchlists. New previews are bytes rather than base64 text, avoiding base64's storage overhead. Original uploads are processed in memory and are not written to Render's ephemeral filesystem. Existing data-URI previews are converted by migration `0003_platform_intelligence` when valid; legacy values remain readable if conversion is impossible.

No private object store is configured. A future object-storage migration must copy and verify previews before clearing database bytes; PlantDoc will not silently redirect persistent uploads to Render's ephemeral disk.

The current free preview database `plantdoc-preview-db` expires on **11 October 2026 at 13:37:40 UTC**. The deployment is not durable. Follow [docs/DATABASE_MIGRATION.md](docs/DATABASE_MIGRATION.md) before that deadline. No paid resource or billing is enabled by this repository.

## API overview

All application endpoints except registration, login and refresh require a Bearer access token.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/users/register/` | Create account |
| POST | `/api/users/login/` | Sign in |
| POST | `/api/users/refresh/` | Renew access |
| GET / PATCH | `/api/users/me/` | Read/update owned profile |
| POST | `/api/plant_doctor_ai/analyze/` | Validate and classify one image |
| GET | `/api/plant_doctor_ai/history/` | Search/filter private diagnoses |
| GET / PATCH / DELETE | `/api/plant_doctor_ai/history/{id}/` | Diagnosis detail/notes/delete |
| GET | `/api/plant_doctor_ai/history/export/` | Owner-scoped CSV export |
| GET | `/api/plant_doctor_ai/analytics/` | Owner-scoped summary |
| GET | `/api/plant_doctor_ai/plants/` | Internal model registry, not visible navigation |
| GET | `/api/plant_doctor_ai/mandi/` | Live mandi filters/sorting/pagination |
| GET | `/api/plant_doctor_ai/mandi/history/` | Stored comparable observations |
| GET | `/api/plant_doctor_ai/weather/` | City or coordinate forecast |
| POST | `/api/plant_doctor_ai/risk/` | Owned cached-weather risk |
| GET / POST | `/api/plant_doctor_ai/watchlist/` | Private watchlist |
| DELETE | `/api/plant_doctor_ai/watchlist/{id}/` | Delete owned item |
| POST | `/api/plant_doctor_ai/chat/` | Context-bound assistant |

## Testing

```bash
cd plant_disease_detector
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

```bash
cd plant_disease_detector_frontend
npm ci
npm run lint
npm run build
npm test
```

Backend tests cover authentication, refresh, owner isolation, inference, image validation/quality rejection, diagnosis persistence, notes, exports, watchlists, mandi sorting/comparison, weather shape, risk-context ownership, Gemini fallback and prevention of invented live values. Frontend tests cover token refresh races and API errors. GitHub Actions repeats the Linux build/test pipeline on pushes and pull requests.

Live provider tests are separate from mocks: Open-Meteo can be checked without credentials; data.gov.in and Gemini require their private Render keys. Provider failures produce visible, non-fabricated fallbacks.

## Render deployment

`render.yaml` defines the existing `shikhar-plantdoc` Python web service in Singapore. Build: `bash scripts/build.sh`; start: `bash scripts/start.sh`; health check: `/healthz`; auto-deploy: after checks pass on `main`.

Before deployment, set `DATA_GOV_IN_API_KEY` and keep `GEMINI_API_KEY` private in the service environment. Because `sync: false` is not re-prompted on Blueprint updates, adding these entries to YAML does not overwrite existing Dashboard values.

Current URL: <https://shikhar-plantdoc.onrender.com>

## Attribution and limitations

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The major remaining blocker is a licence-recorded, duplicate-controlled labelled dataset and adequate training compute for a fair baseline/candidate/field evaluation. Until then, the current 38-class model stays in production with explicit uncertainty and out-of-distribution limitations.
