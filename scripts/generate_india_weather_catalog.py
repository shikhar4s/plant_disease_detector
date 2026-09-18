"""Refresh the bundled India weather-place catalogue from GeoNames CC BY 4.0 data.

Run intentionally when updating the snapshot; production never downloads this file.
"""
import io
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://download.geonames.org/export/dump/'
OUTPUT = Path(__file__).resolve().parents[1] / 'plant_disease_detector' / 'plant_doctor_ai' / 'data' / 'india_weather_cities.json'
PLACE_CODES = {'PPL', 'PPLA', 'PPLA2', 'PPLA3', 'PPLA4', 'PPLC'}


def fetch(name):
    request = urllib.request.Request(BASE + name, headers={'User-Agent': 'PlantDoc/2.0 (https://shikhar-plantdoc.onrender.com)'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    states = {}
    for line in fetch('admin1CodesASCII.txt').decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and fields[0].startswith('IN.'):
            states[fields[0][3:]] = fields[1]

    districts = {}
    for line in fetch('admin2Codes.txt').decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) >= 2 and fields[0].startswith('IN.'):
            districts[fields[0]] = fields[1]

    archive = zipfile.ZipFile(io.BytesIO(fetch('cities500.zip')))
    places = []
    for line in archive.read('cities500.txt').decode('utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) < 19 or fields[8] != 'IN' or fields[7] not in PLACE_CODES or fields[10] not in states:
            continue
        try:
            identifier = int(fields[0])
            latitude, longitude = float(fields[4]), float(fields[5])
            if identifier <= 0 or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                continue
        except ValueError:
            continue
        places.append({
            'id': identifier,
            'name': fields[1],
            'state_code': fields[10],
            'district': districts.get(f'IN.{fields[10]}.{fields[11]}', ''),
            'latitude': latitude,
            'longitude': longitude,
        })

    places.sort(key=lambda row: (states[row['state_code']].casefold(), row['name'].casefold(), row['district'].casefold(), row['id']))
    catalogue = {
        'source': 'GeoNames cities500',
        'source_url': BASE + 'cities500.zip',
        'license_url': 'https://creativecommons.org/licenses/by/4.0/',
        'fetched_at': datetime.now(timezone.utc).date().isoformat(),
        'coverage': 'Populated places above 500 residents and administrative seats in GeoNames; smaller settlements may be absent.',
        'states': [{'code': code, 'name': name} for code, name in sorted(states.items(), key=lambda item: item[1].casefold())],
        'places': places,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(catalogue, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote {len(places)} India places across {len({row["state_code"] for row in places})} states/territories.')


if __name__ == '__main__':
    main()
