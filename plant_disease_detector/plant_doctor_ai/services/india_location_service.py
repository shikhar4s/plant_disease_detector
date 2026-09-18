"""Bundled, attributed Indian weather locations for state-first selection."""
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'data' / 'india_weather_cities.json'


@lru_cache(maxsize=1)
def _catalog():
    with CATALOG_PATH.open(encoding='utf-8') as source:
        payload = json.load(source)
    by_state = defaultdict(list)
    by_id = {}
    for place in payload['places']:
        by_state[place['state_code']].append(place)
        by_id[place['id']] = place
    states = {state['code']: state['name'] for state in payload['states']}
    return payload, states, by_state, by_id


def list_states():
    payload, states, by_state, _ = _catalog()
    return {
        'states': [{'code': code, 'name': name, 'city_count': len(by_state[code])}
                   for code, name in states.items() if by_state[code]],
        'source': payload['source'], 'source_url': payload['source_url'],
        'license_url': payload['license_url'], 'fetched_at': payload['fetched_at'],
        'coverage': payload['coverage'],
    }


def list_cities(state_code):
    payload, states, by_state, _ = _catalog()
    if state_code not in states or not by_state[state_code]:
        raise ValueError('Choose an Indian state or union territory from the list.')
    return {
        'state': {'code': state_code, 'name': states[state_code]},
        'cities': [{'id': place['id'], 'name': place['name'], 'district': place['district']}
                   for place in by_state[state_code]],
        'source': payload['source'], 'fetched_at': payload['fetched_at'],
        'coverage': payload['coverage'],
    }


def get_city(identifier):
    _, states, _, by_id = _catalog()
    place = by_id.get(identifier)
    if place is None:
        return None
    return {
        'id': place['id'], 'name': place['name'],
        'admin1': states[place['state_code']], 'admin2': place['district'],
        'country': 'India', 'country_code': 'IN',
        'latitude': place['latitude'], 'longitude': place['longitude'],
        'timezone': 'Asia/Kolkata',
    }
