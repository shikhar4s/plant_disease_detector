"""Conservative offline GPS country check using GeoNames' simplified India shape."""
import json
import hashlib
import threading
import time
from functools import lru_cache
from pathlib import Path
import requests
from django.core.cache import cache

BOUNDARY_PATH = Path(__file__).resolve().parents[1] / 'data' / 'india_weather_boundary.geojson'
REVERSE_URL = 'https://nominatim.openstreetmap.org/reverse'
REVERSE_HEADERS = {'User-Agent': 'PlantDoc/2.0 (https://shikhar-plantdoc.onrender.com)',
                   'Accept': 'application/json'}
_reverse_lock = threading.Lock()
_last_reverse_request = 0.0


class IndiaGeoProviderError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _polygons():
    with BOUNDARY_PATH.open(encoding='utf-8') as source:
        geometry = json.load(source)
    if geometry['type'] == 'Polygon':
        return [geometry['coordinates']]
    if geometry['type'] == 'MultiPolygon':
        return geometry['coordinates']
    raise ValueError('Unsupported India boundary geometry')


def _inside_ring(longitude, latitude, ring):
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if (y1 > latitude) != (y2 > latitude):
            crossing = x1 + (latitude - y1) * (x2 - x1) / (y2 - y1)
            if longitude < crossing:
                inside = not inside
        previous = current
    return inside


def is_in_india(latitude, longitude):
    if not 6 <= latitude <= 38 or not 68 <= longitude <= 98:
        return False
    for polygon in _polygons():
        if polygon and _inside_ring(longitude, latitude, polygon[0]):
            if not any(_inside_ring(longitude, latitude, hole) for hole in polygon[1:]):
                return True
    return False


def verify_indian_gps(latitude, longitude):
    """Return the attribution of a successful check, or None for non-Indian GPS.

    Only uncertain coastal/border points use a user-triggered, rate-limited reverse
    country lookup. A provider failure never becomes an accepted location.
    """
    if is_in_india(latitude, longitude):
        return 'GeoNames'
    if not 6 <= latitude <= 38 or not 68 <= longitude <= 98:
        return None
    key = 'india-gps-country:' + hashlib.sha256(f'{latitude:.6f},{longitude:.6f}'.encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return 'OpenStreetMap' if cached == 'in' else None
    if not _reverse_lock.acquire(blocking=False):
        raise IndiaGeoProviderError('GPS verification is busy. Please retry or choose a city.')
    global _last_reverse_request
    try:
        if time.monotonic() - _last_reverse_request < 1.1:
            raise IndiaGeoProviderError('GPS verification is busy. Please retry or choose a city.')
        _last_reverse_request = time.monotonic()
        try:
            response = requests.get(REVERSE_URL,
                                    params={'lat': latitude, 'lon': longitude, 'format': 'jsonv2',
                                            'zoom': 3, 'addressdetails': 1},
                                    headers=REVERSE_HEADERS, timeout=(3, 8))
            response.raise_for_status()
            payload = response.json()
            country_code = str(payload.get('address', {}).get('country_code', '')).lower()
        except (requests.RequestException, ValueError, AttributeError, TypeError) as exc:
            raise IndiaGeoProviderError('GPS verification is temporarily unavailable. Choose a city or retry.') from exc
        cache.set(key, country_code or 'unknown', 3600)
        return 'OpenStreetMap' if country_code == 'in' else None
    finally:
        _reverse_lock.release()
