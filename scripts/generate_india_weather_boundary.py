"""Refresh the bundled India GPS boundary from GeoNames CC BY 4.0 data."""
import io
import json
import urllib.request
import zipfile
from pathlib import Path

SOURCE = 'https://download.geonames.org/export/dump/shapes_simplified_low.json.zip'
OUTPUT = Path(__file__).resolve().parents[1] / 'plant_disease_detector' / 'plant_doctor_ai' / 'data' / 'india_weather_boundary.geojson'


def main():
    request = urllib.request.Request(SOURCE, headers={'User-Agent': 'PlantDoc/2.0 (https://shikhar-plantdoc.onrender.com)'})
    with urllib.request.urlopen(request, timeout=90) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    collection = json.loads(archive.read('shapes_simplified_low.json'))
    feature = next(item for item in collection['features'] if item['properties'].get('geoNameId') == '1269750')
    if feature['geometry']['type'] not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Unexpected India boundary geometry')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(feature['geometry'], separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Wrote India {feature["geometry"]["type"]} boundary.')


if __name__ == '__main__':
    main()
