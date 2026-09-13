"""Resolve commodity photographs from Wikimedia Commons with attribution metadata."""
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests
from django.core.cache import cache

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
HEADERS = {'Accept': 'application/json', 'User-Agent': 'PlantDoc/2.0 (+https://shikhar-plantdoc.onrender.com)'}


def _clean(value):
    return re.sub(r'[^\w\s,.-]', '', str(value or '').strip())[:100]


def _resolve_one(commodity):
    name = _clean(commodity)
    if not name:
        return None
    key = 'commodity-image:' + name.casefold()
    cached = cache.get(key)
    if cached is not None:
        return cached
    params = {
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
        'gsrsearch': f'{name} vegetable', 'gsrlimit': 3, 'prop': 'imageinfo',
        'iiprop': 'url|extmetadata', 'iiurlwidth': 640, 'formatversion': 2,
    }
    result = None
    try:
        response = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=(3, 8))
        response.raise_for_status()
        pages = response.json().get('query', {}).get('pages', [])
        for page in pages:
            info = (page.get('imageinfo') or [{}])[0]
            url = info.get('thumburl') or info.get('url')
            if not url or not str(info.get('mime', '')).startswith('image/'):
                continue
            metadata = info.get('extmetadata') or {}
            license_name = str((metadata.get('LicenseShortName') or {}).get('value') or 'See source').strip()
            artist = re.sub('<[^>]+>', '', str((metadata.get('Artist') or {}).get('value') or '')).strip()
            title = str(page.get('title', '')).removeprefix('File:').strip()
            result = {'url': url, 'source_url': 'https://commons.wikimedia.org/wiki/' + quote(page.get('title', ''), safe=':/()'),
                      'title': title, 'license': license_name[:120], 'credit': artist[:160]}
            break
    except (requests.RequestException, ValueError, TypeError):
        result = None
    cache.set(key, result, 7 * 24 * 60 * 60)
    return result


def resolve_commodity_images(commodities):
    unique, seen = [], set()
    for commodity in commodities:
        name = _clean(commodity)
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            unique.append(name)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = pool.map(_resolve_one, unique)
        return dict(zip(unique, values))

