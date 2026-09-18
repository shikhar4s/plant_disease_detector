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
- India-only, state-first city/town selection from a bundled GeoNames catalogue, with Open-Meteo current conditions and a seven-day forecast; an attributed MET Norway forecast is used if Open-Meteo throttles the forecast request.
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
 ├─ Open-Meteo provider → MET Norway forecast fallback on HTTP 429
 ├─ transparent weather-risk rules
 ├─ bounded assistant context + Gemini REST client
 └─ PostgreSQL persistence and owner isolation
```

Production serves the compiled React application and Django API from the same Render web service. WhiteNoise serves static assets; Gunicorn uses one process with three threads so its health check can respond during CPU-bound model inference without loading multiple model copies. The free service still has a 512 MiB memory limit.

## Disease model

The selected artifact is `efficientnet-b0-field-v2`, explicitly recorded and checksum-verified in `deployment_artifacts/selected_model.json`. This is a newly trained EfficientNet-B0 with 38 classes and architecture-specific 224px RGB preprocessing, not a renamed downloaded classifier. It was selected after a corrected field-focused evaluation. Earlier v1 EfficientNet reports had label-mapping and split limitations; those old JSON reports are not reliable promotion evidence.

The experiment uses separate, grouped PlantVillage and PlantDoc training, validation and test data. PlantVillage validation/test accuracy: 97.11% / 97.79%; field validation/test: 70.71% / 65.25%. Field-test macro F1: 64.60%. The same corrected field labels give the legacy CNN 16.10% accuracy, although old training exposure is unknown. See [the evaluation audit](docs/EVALUATION_REVIEW.md) for exact split sizes, class-level reports, confusion matrices and limitations.

The validation-fitted uncertainty gate accepts 36.02% of field test images at 85.88% accuracy: many images deliberately remain uncertain. It is not a validated leaf detector. Model size: 16,722,568 bytes. Separate CPU benchmark: median 289.40ms, p95 354.77ms, peak process RSS 340.57MiB; production memory needs separate verification. No class expansion was made; more labels without suitable data would not improve accuracy. The model is single-label; confidence is not severity.

## External APIs

### Mandi rates

The backend uses the Government of India Open Government Data resource “Current Daily Price of Various Commodities from Various Markets (Mandi),” generated through AGMARKNET. It returns minimum, maximum and modal wholesale price; PlantDoc never describes modal price as an arithmetic average. The source unit is displayed as INR/quintal for this resource.

Commodity cards load photographs on demand from Wikimedia Commons through the backend. Each image links to its Commons page and displays attribution; if no suitable image is returned, the UI shows a neutral fallback tile instead of a fabricated asset.

`DATA_GOV_IN_API_KEY` is required. Requests use connect/read timeouts, 15-minute caching, bounded result windows, schema validation and clear provider errors. Comparisons state whether the provider total exceeded the fetched window.

### Weather

The Weather page loads Indian states and union territories first, then the available cities and towns for the selected state; no name needs to be typed. Its bundled [GeoNames cities500](https://download.geonames.org/export/dump/cities500.zip) snapshot has 6,986 Indian places across 36 states/territories as of 18 September 2026 under CC BY 4.0. Smaller settlements and some names may be absent or outdated; this is not a definitive list of every Indian city. Run `scripts/generate_india_weather_catalog.py` to refresh the snapshot. Raw GPS coordinates are disabled in India-only mode because they do not independently establish a country.

Open-Meteo provides seven-day forecasts: temperature, feels-like temperature, humidity, precipitation, rain probability, wind, weather code and timezone. Its free API is for non-commercial use, with traffic limits and no uptime guarantee; attribution is required under CC BY 4.0. Responses are cached for 10 minutes. When its forecast endpoint returns HTTP 429, the backend temporarily stops retrying it and uses [MET Norway Locationforecast](https://api.met.no/weatherapi/locationforecast/2.0/documentation) with an identifying User-Agent, coordinate rounding, caching through the provider's `Expires` time and [CC BY 4.0 attribution](https://docs.api.met.no/doc/License.html). The MET Norway global feed may not provide rain probability in India: the UI displays available forecast-period precipitation and explicitly leaves probability unavailable. MET conditions and daily highs/lows are normalized from its forecast timeseries; they are not live observations or guaranteed extremes. If both providers fail, the app reports an error rather than manufacturing weather.

The risk rules use humidity, forecast rain/precipitation and temperature as broad weather-favourability signals. They are intentionally not crop-specific disease models. The UI cites the American Phytopathological Society's disease-triangle lesson and peer-reviewed leaf-wetness review; the numeric cutoffs remain a conservative application heuristic, not a validated forecast.

### Gemini

Gemini is optional. `GEMINI_MODEL` defaults to the current stable `gemini-3.6-flash`; `render.yaml` uses the same value so a Blueprint sync cannot restore the prior identifier. Calls use bounded content, timeouts, one bounded retry for transient capacity errors and conservative prompts. Credentials stay in Render and are never logged or committed.

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
| `GEMINI_MODEL` | optional | Defaults to `gemini-3.6-flash` |
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
| GET | `/api/plant_doctor_ai/mandi/options/` | Region-scoped suggestions from observed records |
| POST | `/api/plant_doctor_ai/commodity-images/` | Bounded, attributed image lookup by commodity names |
| GET | `/api/plant_doctor_ai/weather/` | Indian city forecast by selected location ID |
| GET | `/api/plant_doctor_ai/weather/catalog/` | Indian states or all listed cities for a selected `state` code |
| GET | `/api/plant_doctor_ai/weather/locations/` | India-only geocoding search for API compatibility |
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

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [the model audit](docs/EVALUATION_REVIEW.md). The selected model improves the measured field comparison, but is not a universal or guaranteed diagnosis system. Unsupported crops, non-leaf images and serious crop problems require expert review. Future work needs a separately validated leaf/OOD detector and representative regional field data.
