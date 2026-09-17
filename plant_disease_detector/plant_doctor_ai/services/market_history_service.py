"""Comparable history from observations actually received from the market feed."""
from datetime import timedelta

from django.utils import timezone

from ..models import MandiSnapshot
from .mandi_service import SOURCE_NAME, SOURCE_URL


def market_history(params):
    try:
        days = int(params.get('days', 30))
        if days not in {7, 30, 90}:
            raise ValueError()
    except (TypeError, ValueError):
        raise ValueError('Days must be a whole number: 7, 30 or 90.') from None
    fields = ('commodity', 'variety', 'market', 'state', 'district')
    selected = {field: str(params.get(field, '')).strip()[:160] for field in fields}
    response = {'status': 'unavailable', 'message': 'Historical data unavailable', 'points': [],
                'percentage_change': None, 'days': days,
                'scope': 'Same commodity, variety, market, district, state, provider and source unit; stored observations only.',
                'source': {'name': SOURCE_NAME, 'url': SOURCE_URL}}
    if not all(selected.values()):
        return {**response, 'message': 'Select a commodity, variety, market, district and state for comparable history.'}
    today = timezone.localdate()
    query = MandiSnapshot.objects.filter(provider='data.gov.in',
        **{field + '__iexact': value for field, value in selected.items()},
        price_date__gte=today - timedelta(days=days - 1), price_date__lte=today,
        modal_price__isnull=False)
    unit = str(params.get('unit', '')).strip()[:50]
    if unit:
        query = query.filter(unit=unit)
    elif query.order_by().values('unit').distinct().count() > 1:
        return {**response, 'message': 'Select a source unit; records with different units cannot form one trend.'}
    # Providers can change spelling/capitalisation. Keep the latest observation
    # per date rather than treating two same-day rows as a historical trend.
    by_date = {}
    for row in query.order_by('price_date', 'fetched_at')[:1000]:
        by_date[row.price_date] = row
    observations = list(by_date.values())
    points = [{'date': row.price_date.isoformat(), 'modal_price': float(row.modal_price), 'unit': row.unit}
              for row in observations]
    change = None
    if len(points) >= 2 and points[0]['modal_price'] > 0:
        change = round((points[-1]['modal_price'] - points[0]['modal_price']) / points[0]['modal_price'] * 100, 2)
    return {**response, 'status': 'available' if len(points) >= 2 else 'collecting' if points else 'unavailable',
            'message': '' if len(points) >= 2 else 'Collecting history' if points else 'Historical data unavailable',
            'points': points, 'percentage_change': change,
            'fetched_at': max((row.fetched_at for row in observations), default=timezone.now()).isoformat()}

