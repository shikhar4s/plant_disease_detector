#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -r plant_disease_detector/requirements.txt
npm --prefix plant_disease_detector_frontend ci
npm --prefix plant_disease_detector_frontend run build
python plant_disease_detector/manage.py collectstatic --noinput
