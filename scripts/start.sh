#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../plant_disease_detector"
python manage.py migrate --noinput
exec gunicorn plant_disease_detector.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --no-control-socket --workers 1 --threads 1 --timeout 120 --access-logfile - --error-logfile -
