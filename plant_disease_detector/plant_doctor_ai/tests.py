import csv
import io
import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from users.models import User
from .models import AnalysisResult
from .services.care_guide import care_info
from .services.model_service import model_service, class_names

API = '/api/plant_doctor_ai/'
PREDICTION = {
    'disease': 'Tomato___Early_blight', 'confidence': 0.96,
    'top_predictions': [{'label': 'Tomato___Early_blight', 'disease': 'Tomato · Early blight', 'confidence': 0.96}],
}


def image_upload(size=(256, 256), image_format='JPEG'):
    stream = io.BytesIO()
    Image.new('RGB', size, (50, 130, 55)).save(stream, format=image_format)
    return SimpleUploadedFile('leaf.jpg', stream.getvalue(), content_type='image/jpeg')


class PlantApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('owner@example.com', 'Owner', 'Test-password-91')
        self.other = User.objects.create_user('other@example.com', 'Other', 'Test-password-92')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def record(self, user=None, **kwargs):
        data = dict(disease_name='Tomato___Early_blight', confidence=0.96, **care_info('Tomato___Early_blight'))
        data.update(kwargs)
        return AnalysisResult.objects.create(user=user or self.user, **data)

    def test_analysis_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(API + 'analyze/', {'image': image_upload()}).status_code, 401)

    def test_rejects_missing_corrupt_and_fake_image_files(self):
        for file in [None, SimpleUploadedFile('bad.png', b'not an image', content_type='image/png')]:
            data = {} if file is None else {'image': file}
            self.assertEqual(self.client.post(API + 'analyze/', data, format='multipart').status_code, 400)
        self.assertEqual(AnalysisResult.objects.count(), 0)

    def test_rejects_small_unsupported_and_oversized_images(self):
        for file in [image_upload((32, 32)), image_upload(image_format='GIF'),
                     SimpleUploadedFile('large.jpg', b'x' * (10 * 1024 * 1024 + 1), content_type='image/jpeg')]:
            self.assertEqual(self.client.post(API + 'analyze/', {'image': file}, format='multipart').status_code, 400)

    @patch('plant_doctor_ai.views.model_service.predict', return_value=PREDICTION)
    def test_upload_preserves_full_result_without_gemini_key(self, predict):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            response = self.client.post(API + 'analyze/', {'image': image_upload()}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['severity'], 'Unknown')
        self.assertEqual(response.data['prediction_status'], 'possible_disease')
        self.assertTrue(response.data['image_url'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(response.data['guidance_source'], 'care-guide')
        item = self.client.get(API + 'history/').data['results'][0]
        for field in ['recommended_treatment', 'prevention_tips', 'top_predictions', 'image_url']:
            self.assertEqual(item[field], response.data[field])
        self.user.refresh_from_db()
        self.assertEqual((self.user.total_uploads, self.user.total_analyzed), (1, 1))

    @patch('plant_doctor_ai.views.model_service.predict', side_effect=RuntimeError('internal detail'))
    def test_failed_model_does_not_save_a_result_or_expose_exception(self, predict):
        response = self.client.post(API + 'analyze/', {'image': image_upload()}, format='multipart')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('internal detail', str(response.data))
        self.assertEqual(AnalysisResult.objects.count(), 0)
        self.assertEqual(self.client.get(API + 'analytics/').data['summary']['successRate'], 0)

    def test_history_and_details_are_private(self):
        mine = self.record()
        theirs = self.record(self.other)
        response = self.client.get(API + 'history/')
        self.assertEqual([item['id'] for item in response.data['results']], [mine.id])
        for method in ['get', 'patch', 'delete']:
            response = getattr(self.client, method)(API + f'history/{theirs.id}/', {'notes': 'x'} if method == 'patch' else {})
            self.assertEqual(response.status_code, 404)
        self.assertTrue(AnalysisResult.objects.filter(pk=theirs.pk).exists())

    def test_notes_save_but_prediction_fields_are_read_only(self):
        item = self.record()
        response = self.client.patch(API + f'history/{item.id}/',
            {'notes': 'Check again on Friday', 'confidence': 0, 'disease_name': 'Fake'}, format='json')
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.notes, 'Check again on Friday')
        self.assertEqual(item.confidence, 0.96)
        self.assertEqual(item.disease_name, 'Tomato___Early_blight')

    def test_delete_removes_only_owned_result(self):
        mine = self.record()
        theirs = self.record(self.other)
        self.assertEqual(self.client.delete(API + f'history/{mine.id}/').status_code, 204)
        self.assertFalse(AnalysisResult.objects.filter(pk=mine.pk).exists())
        self.assertTrue(AnalysisResult.objects.filter(pk=theirs.pk).exists())

    def test_history_is_paginated_searchable_and_filterable(self):
        for index in range(13):
            self.record(notes='balcony' if index == 0 else '', confidence=0.2 if index == 0 else 0.96)
        self.assertEqual(len(self.client.get(API + 'history/').data['results']), 12)
        self.assertEqual(len(self.client.get(API + 'history/?page=2').data['results']), 1)
        self.assertEqual(self.client.get(API + 'history/?q=balcony').data['count'], 1)
        self.assertEqual(self.client.get(API + 'history/?status=uncertain').data['count'], 1)
        self.assertEqual(self.client.get(API + 'history/?q=early%20blight').data['count'], 13)

    def test_export_is_private_and_escapes_spreadsheet_formulas(self):
        self.record(notes='=HYPERLINK("https://example.com")')
        self.record(self.other, notes='private other user')
        response = self.client.get(API + 'history/export/')
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1][-1].startswith("'="))
        self.assertNotIn('private other user', response.content.decode())

    def test_healthy_and_low_confidence_are_not_disease_severity(self):
        self.assertEqual(self.record(disease_name='Tomato___healthy').prediction_status, 'healthy')
        self.assertEqual(self.record(disease_name='Tomato___healthy', confidence=0.3).prediction_status, 'uncertain')
        dashboard = self.client.get(API + 'analytics/').data
        self.assertIn('statusDistribution', dashboard)
        self.assertNotIn('severityDistribution', dashboard)

    def test_supported_plants_match_the_model_artifact(self):
        response = self.client.get(API + 'plants/')
        self.assertEqual(response.data['classCount'], len(class_names()))
        self.assertEqual(sum(len(item['conditions']) for item in response.data['plants']), len(class_names()))

    def test_chat_has_multilingual_fallback_and_private_context(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            response = self.client.post(API + 'chat/', {'newMessage': 'पानी कब दें?', 'history': []},
                format='json', HTTP_LANGUAGE='hi-IN')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['mode'], 'care-guide')
        self.assertIn('पानी', response.data['response'])
        item = self.record(self.other)
        response = self.client.post(API + 'chat/', {'newMessage': 'help', 'analysisId': item.id}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_chat_rejects_invalid_or_unbounded_history(self):
        for data in [{'newMessage': ''}, {'newMessage': 'a', 'history': [{'role': 'system', 'parts': [{'text': 'x'}]}]},
                     {'newMessage': 'a', 'history': [{'role': 'user', 'parts': [{'text': 'x'}]}] * 21}]:
            self.assertEqual(self.client.post(API + 'chat/', data, format='json').status_code, 400)

    def test_real_model_returns_finite_ranked_probabilities(self):
        result = model_service.predict(Image.new('RGB', (256, 256), (50, 130, 55)))
        self.assertIn(result['disease'], class_names())
        scores = [item['confidence'] for item in result['top_predictions']]
        self.assertEqual(len(scores), 3)
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0 <= score <= 1 for score in scores))


class GeminiIntegrationTests(TestCase):
    def test_valid_ai_treatment_is_preserved(self):
        from .services.gemini_service import gemini_service
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch.object(gemini_service, '_generate', return_value='{"recommended_treatment":"Inspect nearby leaves.","prevention_tips":["Clean tools."]}'):
            guidance = gemini_service.get_treatment_info('Tomato___Early_blight')
        self.assertEqual(guidance['guidance_source'], 'gemini')
        self.assertEqual(guidance['recommended_treatment'], 'Inspect nearby leaves.')

    def test_malformed_ai_treatment_falls_back_without_losing_analysis(self):
        from .services.gemini_service import gemini_service
        for text in ['not-json', '[]', '{"recommended_treatment":false,"prevention_tips":{}}']:
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-only'}), patch.object(gemini_service, '_generate', return_value=text):
                guidance = gemini_service.get_treatment_info('Tomato___Early_blight')
            self.assertEqual(guidance['guidance_source'], 'care-guide')
