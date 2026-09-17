from datetime import timedelta
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from .models import MandiSnapshot
from .services.commodity_image_service import resolve_commodity_images
from .services.mandi_service import _normalise, mandi_options
from .services.market_history_service import market_history


class MarketFeatureTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_custom_resource_does_not_invent_quintal_unit(self):
        row = {'arrival_date': '15/09/2026', 'market': 'Test', 'commodity': 'Tomato', 'modal_price': '1,200'}
        self.assertEqual(_normalise(row, 'custom')['unit'], 'Unspecified')
        self.assertEqual(_normalise({**row, 'unit': 'INR/kg'})['unit'], 'INR/kg')

    def test_official_thumbnail_host_is_allowed_but_lookalikes_are_not(self):
        from .services.commodity_image_service import _safe_image_url
        self.assertIsNotNone(_safe_image_url('https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Patates.jpg'))
        self.assertIsNone(_safe_image_url('https://thumb.wikimedia.org.evil.example/photo.jpg'))

    @patch('plant_doctor_ai.services.mandi_service._fetch')
    def test_options_are_region_scoped_and_explicitly_incomplete(self, fetch):
        fetch.return_value = ({'records': [
            {'state': 'MP', 'district': 'Indore', 'market': 'A', 'commodity': 'Tomato'},
            {'state': 'UP', 'district': 'Agra', 'market': 'B', 'commodity': 'Potato'},
        ], 'fetched_at': '2026-09-15T00:00:00Z'}, False)
        result = mandi_options({'state': 'MP'})
        self.assertEqual(result['options']['district'], ['Indore'])
        self.assertEqual(result['options']['commodity'], ['Tomato'])
        self.assertFalse(result['complete'])

    def test_history_is_collecting_until_two_distinct_dates(self):
        fields = dict(state='MP', district='Indore', market='A', commodity='Tomato', variety='Local', unit='INR/quintal')
        self.assertEqual(market_history(fields)['status'], 'unavailable')
        MandiSnapshot.objects.create(**fields, price_date=timezone.localdate(), modal_price=120)
        self.assertEqual(market_history(fields)['status'], 'collecting')
        MandiSnapshot.objects.create(**fields, price_date=timezone.localdate() - timedelta(days=1), modal_price=100)
        result = market_history(fields)
        self.assertEqual(result['status'], 'available')
        self.assertEqual(result['percentage_change'], 20)
        self.assertEqual(market_history({**fields, 'unit': 'INR/kg'})['points'], [])

    def test_same_date_spelling_variants_do_not_create_a_trend(self):
        fields = dict(state='MP', district='Indore', market='A', commodity='Tomato', variety='Local', unit='INR/quintal')
        MandiSnapshot.objects.create(**fields, price_date=timezone.localdate(), modal_price=100)
        MandiSnapshot.objects.create(**{**fields, 'commodity': 'tomato'}, price_date=timezone.localdate(), modal_price=120)
        result = market_history(fields)
        self.assertEqual(result['status'], 'collecting')
        self.assertEqual(len(result['points']), 1)

    @patch('plant_doctor_ai.services.commodity_image_service.requests.get')
    def test_images_request_mime_and_cache_misses(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'query': {'pages': []}}
        self.assertEqual(resolve_commodity_images(['Tomato']), {'Tomato': None})
        self.assertEqual(resolve_commodity_images(['Tomato']), {'Tomato': None})
        self.assertEqual(get.call_count, 2)
        self.assertIn('mime', get.call_args.kwargs['params']['iiprop'])
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    @patch('plant_doctor_ai.services.commodity_image_service.requests.get')
    def test_image_urls_cannot_point_to_an_arbitrary_host(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'query': {'pages': [{
            'title': 'File:Tomato.jpg', 'imageinfo': [{'mime': 'image/jpeg', 'thumburl': 'https://evil.example/tomato.jpg',
            'extmetadata': {'LicenseShortName': {'value': 'CC BY'}, 'Artist': {'value': 'Test'}}}]}]}}
        self.assertIsNone(resolve_commodity_images(['Tomato'])['Tomato'])

