"""AGMARKNET-backed market prices exposed through data.gov.in."""
import hashlib
import json
import math
import os
import re
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
REQUEST_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'PlantDoc/2.0 (+https://shikhar-plantdoc.onrender.com)',
}


class MandiProviderError(RuntimeError):
    pass


def _text(value, limit=160):
    return str(value or '').strip()[:limit]


def _number(value):
    try:
        result = float(Decimal(str(value).replace(',', '').strip()))
        return result if math.isfinite(result) and 0 <= result < 10000000000 else None
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


def _normalise(record, resource_id=DEFAULT_RESOURCE_ID):
    if not isinstance(record, dict):
        return None
    price_date = _date(record.get('arrival_date') or record.get('price_date'))
    if not price_date or not record.get('commodity') or not record.get('market'):
        return None
    supplied_unit = _text(record.get('unit') or record.get('price_unit'), 50)
    # This specific AGMARKNET resource publishes Rs/quintal; a different resource
    # must supply its own unit. Never silently apply this contract to other data.
    unit = supplied_unit or ('INR/quintal' if resource_id == DEFAULT_RESOURCE_ID else 'Unspecified')
    if unit.casefold().replace(' ', '') in {'rs/quintal', 'rs./quintal', 'inr/quintal', '₹/quintal'}:
        unit = 'INR/quintal'
    return {
        'state': _text(record.get('state')), 'district': _text(record.get('district')),
        'market': _text(record.get('market')), 'commodity': _text(record.get('commodity')),
        'variety': _text(record.get('variety') or 'Unspecified'),
        'min_price': _number(record.get('min_price')), 'max_price': _number(record.get('max_price')),
        'modal_price': _number(record.get('modal_price')), 'unit': unit,
        'price_date': price_date,
    }


def _fetch(filters):
    key = os.getenv('DATA_GOV_IN_API_KEY', '').strip()
    if not key:
        raise MandiProviderError('Mandi prices are not configured. Add DATA_GOV_IN_API_KEY on the server.')
    resource_id = os.getenv('DATA_GOV_IN_RESOURCE_ID', DEFAULT_RESOURCE_ID).strip()
    if not re.fullmatch(r'[a-fA-F0-9-]{36}', resource_id):
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
        response = requests.get(
            API_URL.format(resource_id=resource_id),
            params=params,
            headers=REQUEST_HEADERS,
            timeout=(4, 18),
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MandiProviderError('The government mandi-price provider is temporarily unavailable.') from exc
    if not isinstance(data, dict) or not isinstance(data.get('records'), list):
        raise MandiProviderError('The mandi provider returned an invalid response. Please try again later.')
    records = [item for item in (_normalise(row, resource_id) for row in data['records'][:provider_limit]) if item]
    try:
        total = max(len(records), int(data.get('total', len(records))))
    except (TypeError, ValueError):
        raise MandiProviderError('The mandi provider returned an invalid record count.') from None
    result = {'records': records, 'provider_total': total,
              'received_count': len(data['records'][:provider_limit]),
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
    try:
        page = max(1, int(params.get('page', 1)))
        page_size = min(50, max(5, int(params.get('page_size', 20))))
    except (TypeError, ValueError) as exc:
        raise ValueError('Page and page size must be whole numbers.') from exc
    filters = {key: _text(params.get(key)) for key in ('state', 'district', 'market', 'commodity')}
    payload, cached = _fetch(filters)
    records = list(payload['records'])
    for field, value in filters.items():
        if value:
            records = [row for row in records if row[field].casefold() == value.casefold()]
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
    start = (page - 1) * page_size
    _save_snapshots(records)
    comparison = None
    candidates = [r for r in records if r['modal_price'] is not None]
    if candidates:
        commodity = filters['commodity'] or candidates[0]['commodity']
        commodity_rows = [r for r in candidates if r['commodity'].casefold() == commodity.casefold()]
        latest_date = max(r['price_date'] for r in commodity_rows)
        anchor = next(r for r in commodity_rows if r['price_date'] == latest_date)
        comparable = [r for r in commodity_rows if r['price_date'] == latest_date
                      and r['variety'].casefold() == anchor['variety'].casefold() and r['unit'] == anchor['unit']]
        if comparable:
            highest = max(comparable, key=lambda r: r['modal_price'])
            comparison = {'highest': highest, 'record_count': len(comparable),
                          'scope': 'Same commodity, exact variety, source unit and latest available commodity date; '
                                   'only records in the fetched, filtered provider window are compared.'}
    context_records = records[:100]
    context_id = store_context(user_id, 'mandi', {'records': context_records, 'fetched_at': payload['fetched_at'],
                                                   'source': SOURCE_NAME}, 900)
    return {'results': records[start:start + page_size], 'count': len(records), 'page': page, 'page_size': page_size,
            'next': start + page_size < len(records), 'previous': page > 1, 'comparison': comparison,
            'context_id': context_id, 'source': {'name': SOURCE_NAME, 'url': SOURCE_URL},
            'fetched_at': payload['fetched_at'], 'cached': cached,
            'coverage': {'provider_total': payload['provider_total'], 'fetched_limit': payload['provider_limit'],
                         'received_count': payload.get('received_count', len(payload['records'])),
                         'complete': payload['provider_total'] <= len(payload['records'])}}


def mandi_options(params):
    """Suggestions from real fetched/saved records; this is not a national directory."""
    from ..models import MandiSnapshot
    parents = {key: _text(params.get(key)) for key in ('state', 'district', 'market')}
    payload, cached = _fetch(parents)
    rows = payload['records']
    options = {}
    for field, scope in (('state', ()), ('district', ('state',)),
                         ('market', ('state', 'district')), ('commodity', ('state', 'district', 'market'))):
        saved = MandiSnapshot.objects.all()
        matching = rows
        for parent in scope:
            if parents[parent]:
                saved = saved.filter(**{parent + '__iexact': parents[parent]})
                matching = [r for r in matching if r[parent].casefold() == parents[parent].casefold()]
        values = set(saved.order_by(field).values_list(field, flat=True).distinct()[:500])
        values.update(row[field] for row in matching if row.get(field))
        options[field] = sorted((value for value in values if value), key=str.casefold)[:500]
    return {'options': options, 'cached': cached, 'fetched_at': payload['fetched_at'],
            'scope': 'Suggestions use fetched provider records and previously saved observations; '
                     'they are not an exhaustive directory. You may type another value.',
            'complete': False, 'source': {'name': SOURCE_NAME, 'url': SOURCE_URL}}

