from unittest.mock import patch

from django.test import SimpleTestCase

from .services.weather_service import WeatherProviderError, search_locations, weather


class WeatherLocationTests(SimpleTestCase):
    @patch('plant_doctor_ai.services.weather_service._request')
    def test_ambiguous_city_returns_distinct_regions_and_skips_invalid_coordinates(self, request):
        request.return_value = ({'results': [
            {'id': 1, 'name': 'Rampur', 'admin1': 'Uttar Pradesh', 'country': 'India', 'country_code': 'IN', 'latitude': 28.8, 'longitude': 79},
            {'id': 2, 'name': 'Rampur', 'admin1': 'Himachal Pradesh', 'country': 'India', 'country_code': 'IN', 'latitude': 31.4, 'longitude': 77.6},
            {'id': 3, 'name': 'Invalid', 'latitude': 190, 'longitude': 79},
        ]}, False)
        result = search_locations('Rampur', 'hi')
        self.assertEqual(len(result['locations']), 2)
        self.assertNotEqual(result['locations'][0]['state'], result['locations'][1]['state'])
        self.assertEqual(request.call_args.args[1]['count'], 50)
        self.assertEqual(request.call_args.args[1]['countryCode'], 'IN')
        self.assertEqual(request.call_args.args[1]['language'], 'hi')

    @patch('plant_doctor_ai.services.weather_service._request')
    def test_city_results_retain_region_country_and_unique_location_ids(self, request):
        request.return_value = ({'results': [
            {'id': 1, 'name': 'Indore', 'admin1': 'Madhya Pradesh', 'country': 'India',
             'country_code': 'IN', 'latitude': 22.72, 'longitude': 75.83},
            {'id': 2, 'name': 'Indore', 'admin1': 'West Virginia', 'country': 'United States',
             'country_code': 'US', 'latitude': 38.46, 'longitude': -81.53},
            {'id': 1, 'name': 'Indore', 'admin1': 'Madhya Pradesh', 'country': 'India',
             'country_code': 'IN', 'latitude': 22.72, 'longitude': 75.83},
        ]}, False)
        result = search_locations('Indore')
        self.assertEqual([row['id'] for row in result['locations']], [1])
        self.assertEqual([row['country_code'] for row in result['locations']], ['IN'])
        self.assertEqual([row['state'] for row in result['locations']], ['Madhya Pradesh'])

    @patch('plant_doctor_ai.services.weather_service._request')
    def test_foreign_selected_location_is_rejected_before_forecast(self, request):
        request.return_value = ({'id': 2, 'name': 'Indore', 'country_code': 'US',
                                 'latitude': 38.46, 'longitude': -81.53}, False)
        with self.assertRaisesRegex(WeatherProviderError, 'only for locations in India'):
            weather(17, location_id='2')
        self.assertEqual(request.call_count, 1)

    @patch('plant_doctor_ai.services.weather_service._request')
    @patch('plant_doctor_ai.services.weather_service.verify_indian_gps', return_value=None)
    def test_foreign_gps_coordinates_are_rejected_in_india_only_mode(self, verification, request):
        for latitude, longitude in [(27.72, 85.32), (31.55, 74.34), (6.93, 79.84)]:
            with self.subTest(latitude=latitude, longitude=longitude), self.assertRaisesRegex(WeatherProviderError, 'could not be confirmed inside India'):
                weather(17, latitude=latitude, longitude=longitude)
        request.assert_not_called()
        self.assertEqual(verification.call_count, 3)

    @patch('plant_doctor_ai.services.weather_service.store_context', return_value='owned-context')
    @patch('plant_doctor_ai.services.weather_service._request')
    def test_indian_gps_coordinates_use_exact_location(self, request, context):
        request.return_value = ({'current': {'temperature_2m': 25}, 'daily': {'time': []},
                                 'timezone': 'Asia/Kolkata'}, False)
        result = weather(17, latitude=22.7179, longitude=75.8333)
        self.assertEqual(result['location']['country'], 'India')
        self.assertEqual(result['location']['latitude'], 22.7179)
        self.assertEqual(request.call_count, 1)
        self.assertIn('/forecast', request.call_args.args[0])
        self.assertEqual(context.call_args.args[0], 17)

    @patch('plant_doctor_ai.services.weather_service._request')
    def test_invalid_selection_does_not_call_provider(self, request):
        for identifier in ('-1', 'abc', '3.2', '999999999999'):
            with self.subTest(identifier=identifier), self.assertRaises(WeatherProviderError):
                weather(1, location_id=identifier)
        request.assert_not_called()

    @patch('plant_doctor_ai.services.weather_service.store_context', return_value='owned-context')
    @patch('plant_doctor_ai.services.weather_service._request')
    def test_selected_city_uses_provider_coordinates_and_names(self, request, context):
        request.side_effect = [
            ({'id': 1, 'name': 'Rampur', 'admin1': 'Himachal Pradesh', 'country': 'India', 'country_code': 'IN', 'latitude': 31.4, 'longitude': 77.6}, False),
            ({'current': {'temperature_2m': 25}, 'daily': {'time': []}, 'timezone': 'Asia/Kolkata'}, False),
        ]
        result = weather(17, location_id='1')
        self.assertEqual(result['location']['state'], 'Himachal Pradesh')
        self.assertEqual(request.call_args.args[1]['latitude'], 31.4)
        self.assertEqual(result['context_id'], 'owned-context')
        self.assertEqual(context.call_args.args[0], 17)

    @patch('plant_doctor_ai.services.weather_service._request', return_value=({}, False))
    def test_city_not_found_is_an_empty_list(self, request):
        self.assertEqual(search_locations('Unknown')['locations'], [])

    @patch('plant_doctor_ai.services.weather_service._request')
    def test_direct_city_query_uses_india_filter_and_rejects_foreign_response(self, request):
        request.return_value = ({'results': [{'id': 1, 'name': 'London', 'country_code': 'GB',
                                              'latitude': 51.5, 'longitude': -0.1}]}, False)
        with self.assertRaisesRegex(WeatherProviderError, 'only for locations in India'):
            weather(17, city='London')
        self.assertEqual(request.call_args.args[1]['countryCode'], 'IN')

    @patch('plant_doctor_ai.services.weather_service.store_context', return_value='owned-context')
    @patch('plant_doctor_ai.services.weather_service._met_forecast')
    @patch('plant_doctor_ai.services.weather_service._request')
    def test_rate_limited_forecast_uses_attributed_fallback(self, request, met, context):
        request.side_effect = [
            ({'id': 1, 'name': 'Indore', 'admin1': 'Madhya Pradesh', 'country': 'India',
              'country_code': 'IN', 'latitude': 22.7179, 'longitude': 75.8333,
              'timezone': 'Asia/Kolkata'}, False),
            WeatherProviderError('rate limited', status_code=429),
        ]
        met.return_value = ({'current': {'temperature_2m': 25}, 'forecast': [
            {'date': '2026-09-17', 'precipitation_probability_max': None}],
            'current_units': {}, 'daily_units': {}, 'timezone': 'UTC',
            'source': {'name': 'MET Norway (forecast fallback)', 'url': 'https://api.met.no/'}}, False)
        result = weather(17, location_id='1')
        self.assertEqual(result['source']['name'], 'MET Norway (forecast fallback)')
        self.assertIsNone(result['forecast'][0]['precipitation_probability_max'])
        self.assertEqual(met.call_args.args, (22.7179, 75.8333, 'Asia/Kolkata'))
        self.assertEqual(result['context_id'], 'owned-context')
