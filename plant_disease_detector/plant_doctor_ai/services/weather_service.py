"""Open-Meteo geocoding and forecast client with bounded caching."""
import hashlib
import json
import requests
from django.core.cache import cache
from django.utils import timezone
from .context_store import store_context

SOURCE = {'name': 'Open-Meteo', 'url': 'https://open-meteo.com/'}


class WeatherProviderError(RuntimeError):
    pass


def _request(url, params):
    key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    cached = cache.get('weather:' + key)
    if cached:
        return cached, True
    try:
        response = requests.get(url, params=params, timeout=(4, 15))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get('error'):
            raise ValueError('Invalid weather provider response')
    except (requests.RequestException, ValueError) as exc:
        raise WeatherProviderError('Weather information is temporarily unavailable.') from exc
    cache.set('weather:' + key, result, 600)
    return result, False


def _location_coordinates(location):
    try:
        latitude, longitude = float(location['latitude']), float(location['longitude'])
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError
        return latitude, longitude
    except (TypeError, KeyError, ValueError) as exc:
        raise WeatherProviderError('The selected location is unavailable. Search for it again.') from exc


def search_locations(query, language='en'):
    query = str(query).strip()
    if not 2 <= len(query) <= 120:
        raise WeatherProviderError('Enter a city name between 2 and 120 characters.')
    payload, cached = _request('https://geocoding-api.open-meteo.com/v1/search',
                              {'name': query, 'count': 10, 'language': language[:2], 'format': 'json'})
    locations = []
    items = payload.get('results', [])
    if not isinstance(items, list):
        raise WeatherProviderError('Weather information is temporarily unavailable.')
    for item in items[:10]:
        try:
            latitude, longitude = _location_coordinates(item)
            identifier = int(item['id'])
            name = str(item['name'])[:120]
            if identifier <= 0 or not name:
                continue
        except (WeatherProviderError, KeyError, TypeError, ValueError, AttributeError):
            continue
        locations.append({
            'id': identifier, 'name': name, 'latitude': latitude, 'longitude': longitude,
            'state': str(item.get('admin1', ''))[:120], 'district': str(item.get('admin2', ''))[:120],
            'country': str(item.get('country', ''))[:120], 'country_code': str(item.get('country_code', ''))[:2],
            'timezone': str(item.get('timezone', ''))[:120],
        })
    return {'locations': locations, 'source': SOURCE, 'cached': cached}


def weather(user_id, *, city='', latitude=None, longitude=None, language='en', location_id=None):
    location = None
    cached = False
    if location_id is not None:
        try:
            identifier = int(str(location_id))
            if not 0 < identifier <= 2147483647:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise WeatherProviderError('Choose a valid location from the search results.') from exc
        location, cached = _request('https://geocoding-api.open-meteo.com/v1/get',
                                    {'id': identifier, 'language': language[:2], 'format': 'json'})
        latitude, longitude = _location_coordinates(location)
    elif latitude is None or longitude is None:
        city = str(city).strip()[:120]
        if len(city) < 2:
            raise WeatherProviderError('Enter a city or share a location.')
        geocoded, cached = _request('https://geocoding-api.open-meteo.com/v1/search',
                                   {'name': city, 'count': 1, 'language': language[:2], 'format': 'json'})
        if not geocoded.get('results'):
            raise WeatherProviderError('No matching city was found.')
        location = geocoded['results'][0]
        latitude, longitude = _location_coordinates(location)
    else:
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError) as exc:
            raise WeatherProviderError('Invalid location coordinates.') from exc
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise WeatherProviderError('Invalid location coordinates.')
    params = {
        'latitude': latitude, 'longitude': longitude, 'timezone': 'auto', 'forecast_days': 7,
        'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m',
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max',
    }
    forecast, forecast_cached = _request('https://api.open-meteo.com/v1/forecast', params)
    current = forecast.get('current', {})
    daily = forecast.get('daily', {})
    days = []
    for index, date in enumerate(daily.get('time', [])):
        day = {'date': date}
        for key, values in daily.items():
            if key != 'time':
                day[key] = values[index] if isinstance(values, list) and index < len(values) else None
        days.append(day)
    result = {
        'location': {
            'name': location.get('name') if location else 'Shared location',
            'state': (location or {}).get('admin1', ''), 'country': (location or {}).get('country', ''),
            'latitude': latitude, 'longitude': longitude, 'timezone': forecast.get('timezone'),
        },
        'current': current, 'current_units': forecast.get('current_units', {}), 'forecast': days,
        'daily_units': forecast.get('daily_units', {}), 'source': SOURCE,
        'fetched_at': timezone.now().isoformat(), 'cached': cached and forecast_cached,
    }
    result['context_id'] = store_context(user_id, 'weather', result, 900)
    return result

