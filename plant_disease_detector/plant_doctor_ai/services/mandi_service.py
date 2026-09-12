"""AGMARKNET-backed market prices exposed through data.gov.in."""
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
from django.core.cache import cache
from django.utils import timezone

from .context_store import store_context

SOURCE_NAME = 'AGMARKNET via data.gov.in'
SOURCE_URL = 'https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi'
API_URL = 'https://api.data.gov.in/resource/{resource_id}'
DEFAULT_RESOURCE_ID = '9ef84268-d588-465a-a308-a864a43d0070'


class MandiProviderError(RuntimeError):
    pass


def _text(value, limit=160):
    return str(value or '').strip()[:limit]


def _number(value):
    try:
        return float(Decimal(str(value).replace(',', '').strip()))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _date(value):
    text = _text(value, 30)
    for pattern in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _normalise(record):
    price_date = _date(record.get('arrival_date') or record.get('price_date'))
    if not price_date:
        return None
    return {
        'state': _text(record.get('state')), 'district': _text(record.get('district')),
        'market': _text(record.get('market')), 'commodity': _text(record.get('commodity')),
        'variety': _text(record.get('variety') or 'Unspecified'),
        'min_price': _number(record.get('min_price')), 'max_price': _number(record.get('max_price')),
        'modal_price': _number(record.get('modal_price')), 'unit': 'INR/quintal',
        'price_date': price_date,
    }


def _fetch(filters):
    key = os.getenv('DATA_GOV_IN_API_KEY', '').strip()
    if not key:
        raise MandiProviderError('Mandi prices are not configured. Add DATA_GOV_IN_API_KEY on the server.')
    resource_id = os.getenv('DATA_GOV_IN_RESOURCE_ID', DEFAULT_RESOURCE_ID).strip()
    if not resource_id:
        raise MandiProviderError('The mandi data resource is not configured.')
    try:
        provider_limit = min(max(1, int(os.getenv('MANDI_FETCH_LIMIT', '1000'))), 2000)
    except ValueError as exc:
        raise MandiProviderError('The mandi fetch limit is misconfigured.') from exc
    params = {'api-key': key, 'format': 'json', 'limit': provider_limit, 'offset': 0}
    field_map = {'state': 'state', 'district': 'district', 'market': 'market', 'commodity': 'commodity'}
    for local, remote in field_map.items():
        if filters.get(local):
            params[f'filters[{remote}]'] = filters[local]
    fingerprint = hashlib.sha256(json.dumps({**params, 'api-key': 'redacted'}, sort_keys=True).encode()).hexdigest()
    cached = cache.get('mandi-provider:' + fingerprint)
    if cached:
        return cached, True
    try:
        response = requests.get(API_URL.format(resource_id=resource_id), params=params, timeout=(4, 18))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MandiProviderError('The government mandi-price provider is temporarily unavailable.') from exc
    records = [item for item in (_normalise(row) for row in data.get('records', [])) if item]
    result = {'records': records, 'provider_total': int(data.get('total') or len(records)),
              'provider_limit': params['limit'], 'fetched_at': timezone.now().isoformat()}
    cache.set('mandi-provider:' + fingerprint, result, 900)
    return result, False


def _save_snapshots(records):
    from ..models import MandiSnapshot
    for item in records[:1000]:
        MandiSnapshot.objects.update_or_create(
            provider='data.gov.in', state=item['state'], district=item['district'], market=item['market'],
            commodity=item['commodity'], variety=item['variety'], price_date=item['price_date'],
            defaults={key: item[key] for key in ('min_price', 'max_price', 'modal_price', 'unit')})


def search_mandi(user_id, params):
    filters = {key: _text(params.get(key)) for key in ('state', 'district', 'market', 'commodity')}
    payload, cached = _fetch(filters)
    records = payload['records']
    search = _text(params.get('q')).casefold()
    variety = _text(params.get('variety')).casefold()
    date_value = _text(params.get('date'), 20)
    if search:
        records = [r for r in records if search in ' '.join(str(v) for v in r.values()).casefold()]
    if variety:
        records = [r for r in records if variety in r['variety'].casefold()]
    if date_value:
        records = [r for r in records if r['price_date'] == date_value]
    sort = params.get('sort', 'newest')
    if sort == 'highest':
        records.sort(key=lambda r: (r['modal_price'] is not None, r['modal_price'] or -1), reverse=True)
    elif sort == 'lowest':
        records.sort(key=lambda r: (r['modal_price'] is None, r['modal_price'] or 0))
    elif sort == 'alphabetical':
        records.sort(key=lambda r: (r['commodity'].casefold(), r['market'].casefold()))
    else:
        records.sort(key=lambda r: r['price_date'], reverse=True)
    try:
        page = max(1, int(params.get('page', 1)))
        page_size = min(50, max(5, int(params.get('page_size', 20))))
    except (TypeError, ValueError) as exc:
        raise ValueError('Page and page size must be whole numbers.') from exc
    start = (page - 1) * page_size
    _save_snapshots(records)
    comparison = None
    candidates = [r for r in records if r['modal_price'] is not None]
    if candidates:
        latest_date = max(r['price_date'] for r in candidates)
        commodity = filters['commodity'] or candidates[0]['commodity']
        comparable = [r for r in candidates if r['price_date'] == latest_date and r['commodity'].casefold() == commodity.casefold()]
        if variety:
            comparable = [r for r in comparable if variety in r['variety'].casefold()]
        if comparable:
            highest = max(comparable, key=lambda r: r['modal_price'])
            comparison = {'highest': highest, 'record_count': len(comparable),
                          'scope': 'Same commodity, unit and latest available date in the fetched provider window' +
                                   ('; variety filter applied.' if variety else '; varieties may differ unless filtered.')}
    context_records = records[:100]
    context_id = store_context(user_id, 'mandi', {'records': context_records, 'fetched_at': payload['fetched_at'],
                                                   'source': SOURCE_NAME}, 900)
    return {'results': records[start:start + page_size], 'count': len(records), 'page': page, 'page_size': page_size,
            'next': start + page_size < len(records), 'previous': page > 1, 'comparison': comparison,
            'context_id': context_id, 'source': {'name': SOURCE_NAME, 'url': SOURCE_URL},
            'fetched_at': payload['fetched_at'], 'cached': cached,
            'coverage': {'provider_total': payload['provider_total'], 'fetched_limit': payload['provider_limit'],
                         'complete': payload['provider_total'] <= payload['provider_limit']}}
