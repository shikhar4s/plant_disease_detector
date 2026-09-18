"""Open-Meteo geocoding and forecast client with bounded caching."""
import hashlib
import json
import logging
from datetime import datetime, timezone as utc_timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import requests
from django.core.cache import cache
from django.utils import timezone
from .context_store import store_context

SOURCE = {'name': 'Open-Meteo', 'url': 'https://open-meteo.com/',
          'license': 'https://creativecommons.org/licenses/by/4.0/'}
MET_SOURCE = {'name': 'MET Norway (forecast fallback)',
              'url': 'https://api.met.no/weatherapi/locationforecast/2.0/documentation',
              'license': 'https://creativecommons.org/licenses/by/4.0/'}
MET_URL = 'https://api.met.no/weatherapi/locationforecast/2.0/complete'
MET_HEADERS = {'User-Agent': 'PlantDoc/2.0 (https://shikhar-plantdoc.onrender.com)',
               'Accept': 'application/json'}
logger = logging.getLogger(__name__)


class WeatherProviderError(RuntimeError):
    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def _request(url, params):
    key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    cached = cache.get('weather:' + key)
    if cached:
        return cached, True
    if cache.get('weather-limited:' + key):
        raise WeatherProviderError('Open-Meteo is rate limiting weather forecasts.', status_code=429)
    try:
        response = requests.get(url, params=params, timeout=(4, 15))
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or result.get('error'):
            raise ValueError('Invalid weather provider response')
    except (requests.RequestException, ValueError) as exc:
        # Never log provider query parameters (which may contain coordinates).
        response = getattr(exc, 'response', None)
        logger.warning('Weather provider %s failed: %s, HTTP %s', url.split('/')[2],
                       type(exc).__name__, getattr(response, 'status_code', None))
        status_code = getattr(response, 'status_code', None)
        if status_code == 429:
            cache.set('weather-limited:' + key, True, 120)
        raise WeatherProviderError('Weather information is temporarily unavailable.', status_code=status_code) from exc
    cache.set('weather:' + key, result, 600)
    return result, False


def _met_weather_code(symbol):
    """Map MET's broad symbol families to the existing WMO-style display groups."""
    symbol = str(symbol or '').lower()
    if 'thunder' in symbol:
        return 95
    if 'snow' in symbol:
        return 75
    if 'rainshowers' in symbol or 'sleetshowers' in symbol:
        return 80
    if 'rain' in symbol or 'sleet' in symbol:
        return 63
    if 'fog' in symbol:
        return 45
    if 'cloudy' in symbol:
        return 3 if symbol.startswith('cloudy') else 2
    if 'fair' in symbol:
        return 2
    return 0 if 'clearsky' in symbol else None


def _met_forecast(latitude, longitude, timezone_name):
    """Use a separately attributed forecast only when Open-Meteo throttles us."""
    lat, lon = round(latitude, 4), round(longitude, 4)
    key = f'met-forecast:{lat}:{lon}:{timezone_name}'
    cached = cache.get(key)
    if cached:
        return cached, True
    try:
        response = requests.get(MET_URL, params={'lat': lat, 'lon': lon},
                                headers=MET_HEADERS, timeout=(4, 15))
        response.raise_for_status()
        payload = response.json()
        series = payload['properties']['timeseries']
        if not isinstance(series, list) or not series:
            raise ValueError('No forecast series')
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.warning('MET Norway forecast failed: %s, HTTP %s', type(exc).__name__,
                       getattr(getattr(exc, 'response', None), 'status_code', None))
        raise WeatherProviderError('Weather information is temporarily unavailable.') from exc
    try:
        local_tz = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        timezone_name, local_tz = 'UTC', utc_timezone.utc
    days = {}
    now = timezone.now().astimezone(local_tz)
    for item in series[:240]:
        try:
            date = datetime.fromisoformat(item['time'].replace('Z', '+00:00')).astimezone(local_tz).date()
            details = item['data']['instant']['details']
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if not 0 <= (date - now.date()).days < 7:
            continue
        day = days.setdefault(date.isoformat(), {'temperatures': [], 'conditions': [], 'precipitation': []})
        if isinstance(details.get('air_temperature'), (int, float)):
            day['temperatures'].append(details['air_temperature'])
        data = item['data']
        period = data.get('next_1_hours') or data.get('next_6_hours') or {}
        amount = period.get('details', {}).get('precipitation_amount')
        if isinstance(amount, (int, float)) and amount >= 0:
            day['precipitation'].append(amount)
        symbol = (period.get('summary') or data.get('next_12_hours', {}).get('summary') or {}).get('symbol_code')
        code = _met_weather_code(symbol)
        if code is not None:
            day['conditions'].append(code)
    first = series[0]['data']
    details = first['instant']['details']
    first_period = first.get('next_1_hours') or {}
    current = {
        'time': series[0]['time'],
        'temperature_2m': details.get('air_temperature'),
        'apparent_temperature': details.get('apparent_air_temperature'),
        'relative_humidity_2m': details.get('relative_humidity'),
        'precipitation': (first_period.get('details') or {}).get('precipitation_amount'),
        'rain': None,
        'wind_speed_10m': round(details['wind_speed'] * 3.6, 1) if isinstance(details.get('wind_speed'), (int, float)) else None,
        'weather_code': _met_weather_code((first_period.get('summary') or {}).get('symbol_code')),
    }
    forecast = [{'date': date, 'temperature_2m_max': max(row['temperatures']) if row['temperatures'] else None,
                 'temperature_2m_min': min(row['temperatures']) if row['temperatures'] else None,
                 'precipitation_sum': round(sum(row['precipitation']), 1) if row['precipitation'] else None,
                 'precipitation_probability_max': None,
                 'weather_code': row['conditions'][0] if row['conditions'] else None}
                for date, row in sorted(days.items())]
    if not forecast or current['temperature_2m'] is None:
        raise WeatherProviderError('Weather information is temporarily unavailable.')
    result = {'current': current, 'current_units': {'temperature_2m': '°C', 'apparent_temperature': '°C',
               'relative_humidity_2m': '%', 'precipitation': 'mm', 'wind_speed_10m': 'km/h'},
              'forecast': forecast, 'daily_units': {'temperature_2m_max': '°C', 'temperature_2m_min': '°C',
               'precipitation_sum': 'mm'}, 'source': MET_SOURCE, 'timezone': timezone_name}
    expires = response.headers.get('Expires')
    try:
        ttl = max(60, min(7200, int((parsedate_to_datetime(expires) - datetime.now(utc_timezone.utc)).total_seconds())))
    except (TypeError, ValueError, OverflowError):
        ttl = 1800
    cache.set(key, result, ttl)
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
                              {'name': query, 'count': 50, 'language': language[:2], 'format': 'json'})
    locations = []
    items = payload.get('results', [])
    if not isinstance(items, list):
        raise WeatherProviderError('Weather information is temporarily unavailable.')
    seen_ids = set()
    for item in items[:50]:
        try:
            latitude, longitude = _location_coordinates(item)
            identifier = int(item['id'])
            name = str(item['name'])[:120]
            if identifier <= 0 or not name or identifier in seen_ids:
                continue
        except (WeatherProviderError, KeyError, TypeError, ValueError, AttributeError):
            continue
        seen_ids.add(identifier)
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
    fallback = None
    try:
        forecast, forecast_cached = _request('https://api.open-meteo.com/v1/forecast', params)
    except WeatherProviderError as exc:
        if exc.status_code != 429:
            raise
        fallback, forecast_cached = _met_forecast(latitude, longitude, (location or {}).get('timezone') or 'UTC')
    if fallback:
        current, days = fallback['current'], fallback['forecast']
    else:
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
            'latitude': latitude, 'longitude': longitude,
            'timezone': fallback['timezone'] if fallback else forecast.get('timezone'),
        },
        'current': current, 'current_units': fallback['current_units'] if fallback else forecast.get('current_units', {}),
        'forecast': days, 'daily_units': fallback['daily_units'] if fallback else forecast.get('daily_units', {}),
        'source': fallback['source'] if fallback else SOURCE,
        'fetched_at': timezone.now().isoformat(), 'cached': cached and forecast_cached,
    }
    result['context_id'] = store_context(user_id, 'weather', result, 900)
    return result

