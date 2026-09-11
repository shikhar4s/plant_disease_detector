# PlantDoc — Plant Disease Detector

PlantDoc uses the project's trained CNN to suggest possible plant disease matches from leaf photos. The React interface and Django API can run together as one web service.

**Developer: Shikhar Shrivastava**

## Features

- Sign-up, sign-in, automatic session renewal, and saved profile names and photos.
- Validated JPEG, PNG and WebP uploads; camera input on supported devices.
- The three most likely trained classes with model confidence.
- Private, paginated analysis history with search, status filters and deletion.
- Saved follow-up notes, individual text reports and filtered CSV exports.
- A searchable catalogue generated directly from the trained class labels.
- Analytics calculated from account records.
- English, Hindi, Spanish and French language choices.
- Optional Gemini treatment guidance and contextual chat. A clearly labelled built-in care guide works without a key or when the provider fails.

## Model limits

The active weights are `plant_disease_detector/deployment_artifacts/plant_disease_model.pth`; class labels come from the adjacent JSON file. The original CNN architecture and RGB, bilinear 256 × 256, [0, 1] preprocessing are retained.

The classifier always picks from its supported classes. It cannot reliably identify unrelated images or unsupported plants. Confidence is neither disease severity nor a calibrated guarantee of accuracy. Results below 70% are marked uncertain; this threshold is a display heuristic, not a validated diagnostic boundary. Severity and recovery time are not estimated from a photo. No new accuracy claim is made without a labelled evaluation set.

## Run locally

Requires Python 3.12 and Node.js 22. The pinned Torch wheel is CPU-only.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r plant_disease_detector/requirements.txt
python plant_disease_detector/manage.py migrate
python plant_disease_detector/manage.py runserver
```

On Windows, activate with `.venv\Scripts\activate`.

In another terminal:

```bash
cd plant_disease_detector_frontend
npm ci
npm run dev
```

Vite forwards `/api` requests to Django on port 8000. For separate hosting, set `VITE_API_BASE_URL` before building and configure `CORS_ALLOWED_ORIGINS` on the backend.

## Configuration and storage

Copy the backend `.env.example` to `.env` for local overrides. Never commit credentials.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required strong random secret in production |
| `DEBUG` | Use `false` when hosted |
| `DATABASE_URL` | Required persistent PostgreSQL connection in production |
| `ALLOWED_HOSTS` | Comma-separated extra hostnames; Render's hostname is added automatically |
| `CORS_ALLOWED_ORIGINS` | Frontend origins when the frontend is hosted separately |
| `GEMINI_API_KEY` | Optional; set privately in the hosting dashboard |
| `GEMINI_MODEL` | Defaults to `gemini-2.5-flash` |

Account data, notes and compressed image previews are stored in PostgreSQL when hosted. Original uploads are processed in memory and not kept. Previews are returned only through authenticated owner-scoped APIs. Production refuses to start without a persistent database; local SQLite files must not be deployed.

Gemini receives text conversation history and the selected prediction label/confidence, not leaf image files. Without a configured key, chat provides a limited built-in guide rather than open-ended AI responses.

## Hosting on Render

The committed `render.yaml` defines one free Python web service, serves the built frontend on the same origin, generates the Django secret and links the existing `plantdoc-preview-db` database in Shikhar's workspace. Apply it using:

[Deploy the Blueprint](https://dashboard.render.com/blueprint/new?repo=https://github.com/shikhar4s/plant_disease_detector)

The preview database was created on **11 September 2026** and expires on **11 October 2026**. This is a temporary preview configuration. Before expiry, migrate to a lasting PostgreSQL database such as your Neon project or upgrade the Render database. Remove the Blueprint's `fromDatabase` binding if switching `DATABASE_URL` to Neon, so future syncs cannot reset it. Free web services also sleep after inactivity. [Render free-instance limits](https://render.com/docs/free).

Set `GEMINI_API_KEY` in the web service's Environment page to enable AI treatment guidance and full chat; otherwise the built-in guide is available. No API key is needed to classify leaves.

Build: `bash scripts/build.sh`. Start: `bash scripts/start.sh`. Health check: `/healthz`.
One worker keeps inference memory bounded on the free instance. A Dockerfile is also included for Docker hosting.

## Verification

```bash
cd plant_disease_detector
python manage.py collectstatic --noinput
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

Backend regressions cover real CNN inference, upload errors, ownership isolation, persistence, filtering, CSV formula escaping, authentication, profile updates and AI fallback behavior. Frontend API tests cover refresh, concurrent expired requests, logout races and error handling. GitHub Actions runs these checks for pushes and pull requests.

## API

All plant and profile endpoints require a Bearer access token.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/users/register/` | Create account |
| POST | `/api/users/login/` | Sign in |
| POST | `/api/users/refresh/` | Renew access |
| GET / PATCH | `/api/users/me/` | Profile and photo |
| POST | `/api/plant_doctor_ai/analyze/` | Classify uploaded leaf |
| GET | `/api/plant_doctor_ai/history/` | Private searchable history |
| GET / PATCH / DELETE | `/api/plant_doctor_ai/history/{id}/` | Read, annotate or delete a result |
| GET | `/api/plant_doctor_ai/history/export/` | Export filtered history |
| GET | `/api/plant_doctor_ai/analytics/` | Account analytics |
| GET | `/api/plant_doctor_ai/plants/` | Supported classes |
| POST | `/api/plant_doctor_ai/chat/` | Contextual assistant |
