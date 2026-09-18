from unittest.mock import patch

from django.test import SimpleTestCase

from .services.india_location_service import get_city, list_cities, list_states
from .services.weather_service import weather


class IndiaWeatherCatalogTests(SimpleTestCase):
    def test_states_and_cities_load_without_a_search_term(self):
        response = list_states()
        self.assertEqual(len(response['states']), 36)
        self.assertGreater(sum(state['city_count'] for state in response['states']), 6000)
        madhya_pradesh = next(state for state in response['states'] if state['name'] == 'Madhya Pradesh')
        cities = list_cities(madhya_pradesh['code'])['cities']
        self.assertEqual(len(cities), madhya_pradesh['city_count'])
        self.assertTrue(any(city['name'] == 'Indore' for city in cities))
        self.assertEqual(get_city(1269743)['country_code'], 'IN')

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            list_cities('US')

    @patch('plant_doctor_ai.services.weather_service.store_context', return_value='owned-context')
    @patch('plant_doctor_ai.services.weather_service._request')
    def test_catalogue_city_forecast_uses_bundled_indian_coordinates(self, request, context):
        request.return_value = ({'current': {'temperature_2m': 25}, 'daily': {'time': []},
                                 'timezone': 'Asia/Kolkata'}, False)
        result = weather(17, location_id='1269743')
        self.assertEqual(result['location']['name'], 'Indore')
        self.assertEqual(result['location']['state'], 'Madhya Pradesh')
        self.assertEqual(request.call_count, 1)
        self.assertIn('/forecast', request.call_args.args[0])
        self.assertAlmostEqual(request.call_args.args[1]['latitude'], 22.7179, places=3)
        self.assertEqual(context.call_args.args[0], 17)
