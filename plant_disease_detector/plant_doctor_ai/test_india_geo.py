from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase

from .services.india_geo_service import is_in_india, verify_indian_gps


class IndiaGeoTests(SimpleTestCase):
    def test_known_indian_cities_and_island_are_inside(self):
        for latitude, longitude in [(22.7179, 75.8333), (19.07, 72.88),
                                    (28.61, 77.21), (10.83522, 72.18217), (11.66613, 92.74635)]:
            with self.subTest(latitude=latitude, longitude=longitude):
                self.assertTrue(is_in_india(latitude, longitude))

    def test_neighbouring_countries_are_outside(self):
        for latitude, longitude in [(27.72, 85.32), (31.55, 74.34),
                                    (6.93, 79.84), (23.81, 90.41)]:
            with self.subTest(latitude=latitude, longitude=longitude):
                self.assertFalse(is_in_india(latitude, longitude))

    def test_inland_indian_point_skips_reverse_provider(self):
        with patch('plant_doctor_ai.services.india_geo_service.requests.get') as get:
            self.assertEqual(verify_indian_gps(22.7179, 75.8333), 'GeoNames')
            get.assert_not_called()

    @patch('plant_doctor_ai.services.india_geo_service.time.monotonic', return_value=10000)
    @patch('plant_doctor_ai.services.india_geo_service.requests.get')
    def test_coastal_indian_point_uses_attributed_reverse_country_check(self, get, monotonic):
        cache.clear()
        get.return_value = Mock(json=lambda: {'address': {'country_code': 'in'}})
        self.assertFalse(is_in_india(10.56688, 72.64203))
        self.assertEqual(verify_indian_gps(10.56688, 72.64203), 'OpenStreetMap')
        self.assertEqual(verify_indian_gps(10.56688, 72.64203), 'OpenStreetMap')
        get.assert_called_once()

    @patch('plant_doctor_ai.services.india_geo_service.time.monotonic', return_value=20000)
    @patch('plant_doctor_ai.services.india_geo_service.requests.get')
    def test_neighbouring_country_reverse_result_is_rejected(self, get, monotonic):
        cache.clear()
        get.return_value = Mock(json=lambda: {'address': {'country_code': 'np'}})
        self.assertIsNone(verify_indian_gps(27.72, 85.32))
        self.assertIsNone(verify_indian_gps(27.72, 85.32))
        get.assert_called_once()
