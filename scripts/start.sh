#!/usr/bin/env bash
set -euo pipefail
# Shell scripts are checked in with LF line endings for Linux hosting.
cd "$(dirname "$0")/../plant_disease_detector"
python manage.py migrate --noinput
exec gunicorn plant_disease_detector.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --no-control-socket --worker-class gthread --workers 1 --threads 3 --timeout 120 --access-logfile - --error-logfile -

