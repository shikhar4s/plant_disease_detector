from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from .models import User


class AccountTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {'email': 'PlantOwner@example.com', 'full_name': 'Plant Owner',
                        'password': 'Green-leaf-test-839!', 'confirm_password': 'Green-leaf-test-839!'}

    def test_signup_login_refresh_and_profile_rehydration(self):
        response = self.client.post('/api/users/register/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['user']['name'], 'Plant Owner')
        self.assertEqual(response.data['user']['email'], 'plantowner@example.com')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        profile = self.client.get('/api/users/me/')
        self.assertEqual(profile.status_code, 200)
        self.assertTrue(profile.data['date_joined'])
        updated = self.client.patch('/api/users/me/', {'full_name': 'Updated Owner', 'is_staff': True}, format='json')
        self.assertEqual(updated.data['name'], 'Updated Owner')
        self.assertFalse(User.objects.get().is_staff)
        refreshed = self.client.post('/api/users/refresh/', {'refresh': response.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 200)
        self.client.credentials()
        login = self.client.post('/api/users/login/', {'email': 'PLANTOWNER@example.com',
            'password': self.payload['password']}, format='json')
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['name'], 'Updated Owner')

    def test_duplicate_email_and_weak_password_are_rejected(self):
        self.client.post('/api/users/register/', self.payload, format='json')
        self.assertEqual(self.client.post('/api/users/register/',
            {**self.payload, 'email': 'plantowner@example.com'}, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/users/register/', {**self.payload,
            'email': 'new@example.com', 'password': '1234', 'confirm_password': '1234'}, format='json').status_code, 400)

    def test_profile_and_photo_persist(self):
        from plant_doctor_ai.tests import image_upload
        user = User.objects.create_user('profile@example.com', 'Profile', 'Strong-password-53')
        self.client.force_authenticate(user)
        response = self.client.patch('/api/users/me/', {'photo': image_upload()}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['photo_url'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(self.client.get('/api/users/me/').data['photo_url'], response.data['photo_url'])

    def test_invalid_tokens_do_not_break_public_login_and_invalid_refresh_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired')
        response = self.client.post('/api/users/register/', self.payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.post('/api/users/refresh/', {'refresh': 'bad'}, format='json').status_code, 401)
