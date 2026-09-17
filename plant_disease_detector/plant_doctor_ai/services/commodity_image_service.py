"""Bounded, attributed commodity photo discovery using Wikimedia Commons."""
import hashlib
import html
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit

import requests
from django.core.cache import cache

COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
WIKIPEDIA_API = 'https://en.wikipedia.org/w/api.php'
HEADERS = {'Accept': 'application/json', 'User-Agent': 'PlantDoc/2.1 (+https://shikhar-plantdoc.onrender.com)'}
# Search synonyms, not a manually maintained image catalogue.
SEARCH_NAMES = {'brinjal': 'eggplant', 'bhindi': 'okra', 'bengal gram': 'chickpea',
                'black gram': 'vigna mungo', 'green gram': 'mung bean', 'arhar': 'pigeon pea',
                'paddy': 'rice', 'soyabean': 'soybean', 'groundnut': 'peanut',
                'bajra': 'pearl millet', 'jowar': 'sorghum', 'mosambi': 'sweet lime'}


def _plain(value, limit=180):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', str(value or '')))).strip()[:limit]


def _clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()[:160]


def _safe_image_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    if parsed.scheme == 'https' and parsed.netloc in {'upload.wikimedia.org', 'thumb.wikimedia.org'}:
        return value
    return None


def _resolve_one(commodity):
    name = _clean(commodity)
    if not name:
        return None
    key = 'commodity-image:v5:' + hashlib.sha256(name.casefold().encode()).hexdigest()
    cached = cache.get(key)
    if isinstance(cached, dict) and 'image' in cached:
        return cached['image']  # None is a cached miss, not another network request.
    searchable = re.sub(r'\([^)]*\)', '', name).strip().casefold()
    searchable = SEARCH_NAMES.get(searchable, searchable)
    searchable = ' '.join(re.findall(r'[\w]+', searchable))[:100]
    if not searchable:
        return None
    params = {
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6,
        'gsrsearch': f'intitle:{searchable} filetype:bitmap -intitle:geograph -intitle:beach -intitle:map', 'gsrlimit': 5, 'prop': 'imageinfo',
        'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 640, 'formatversion': 2,
        'iiextmetadatafilter': 'LicenseShortName|Artist|Attribution',
    }
    result, ttl = None, 600
    try:
        # An article's representative photo is less ambiguous than full-text
        # photo search (which can return machinery or places named after food).
        exact_title = None
        try:
            article = requests.get(WIKIPEDIA_API, params={'action': 'query', 'format': 'json',
                'formatversion': 2, 'titles': searchable[:1].upper() + searchable[1:],
                'redirects': 1, 'prop': 'pageimages', 'piprop': 'name'},
                headers=HEADERS, timeout=(2, 4), allow_redirects=False)
            if article.status_code == 200:
                article_data = article.json()
                for page in article_data.get('query', {}).get('pages', []):
                    if isinstance(page, dict) and isinstance(page.get('pageimage'), str):
                        exact_title = 'File:' + page['pageimage'][:300]
                        break
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            pass  # An optional article lookup must not disable Commons search.
        if exact_title:
            params = {key: value for key, value in params.items() if key != 'generator' and not key.startswith('gsr')}
            params['titles'] = exact_title
        response = requests.get(COMMONS_API, params=params, headers=HEADERS, timeout=(3, 8), allow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Unexpected image provider status')
        payload = response.json()
        pages = payload.get('query', {}).get('pages', []) if isinstance(payload, dict) else []
        if not isinstance(pages, list):
            pages = []
        for page in sorted((p for p in pages if isinstance(p, dict)), key=lambda p: p.get('index', 100)):
            imageinfo = page.get('imageinfo')
            if not isinstance(imageinfo, list) or not imageinfo or not isinstance(imageinfo[0], dict):
                continue
            info = imageinfo[0]
            url = _safe_image_url(info.get('thumburl') or info.get('url'))
            if not url or info.get('mime') not in {'image/jpeg', 'image/png', 'image/webp'}:
                continue
            title = _plain(page.get('title'), 240)
            words = set(searchable.split())
            title_words = set(re.findall(r'\w+', title.casefold().replace('_', ' ')))
            if not exact_title and not any(word in title_words or word + 's' in title_words or word + 'es' in title_words for word in words):
                continue  # Avoid unrelated hits whose page body merely mentions a crop.
            metadata = info.get('extmetadata')
            if not isinstance(metadata, dict):
                continue
            def meta(field):
                value = metadata.get(field)
                return _plain(value.get('value')) if isinstance(value, dict) else ''
            license_name, credit = meta('LicenseShortName'), meta('Artist') or meta('Attribution')
            if not credit and license_name.casefold() in {'public domain', 'cc0'}:
                credit = 'Public domain · see source page'
            if not license_name or not credit:
                continue
            result = {'url': url, 'source_url': 'https://commons.wikimedia.org/wiki/' + quote(title, safe=''),
                      'title': title.removeprefix('File:'), 'license': license_name, 'credit': credit}
            ttl = 7 * 24 * 60 * 60
            break
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        ttl = 120
    cache.set(key, {'image': result}, ttl)
    return result


def resolve_commodity_images(commodities):
    unique, seen = [], set()
    for commodity in commodities:
        name = _clean(commodity)
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            unique.append(name)
    if not unique:
        return {}
    unique = unique[:30]
    with ThreadPoolExecutor(max_workers=6) as pool:
        values = pool.map(_resolve_one, unique)
        return dict(zip(unique, values))

