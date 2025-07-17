from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock
import json

# ✅ Test sur l’API Produits
class ProductAPITest(TestCase):
    def test_products_endpoint(self):
        # Utilisation du namespace défini dans urls.py : app_name = 'scraping_data'
        url = reverse('scraping_data:product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIsInstance(data, list)

        # Vérifie uniquement si la liste n'est pas vide
        if len(data) > 0:
            # Ton API renvoie un champ 'title' et pas 'name'
            self.assertIn('title', data[0])


# ✅ Tests pour les nouvelles routes test_endpoint et download_history
class APITestCase(TestCase):
    def setUp(self):
        # Initialise un client de test Django
        self.client = Client()

    @patch('requests.request')
    def test_test_endpoint(self, mock_request):
        # Liste de cas de tests à simuler
        test_cases = [
            (
                "GET",
                "https://api.nasa.gov/planetary/apod",
                {"api_key": "DEMO_KEY", "date": "2025-07-14"},
                {},
                {},
                {},
                200,
                '{"date": "2025-07-14", "title": "Test Image", "url": "https://apod.nasa.gov/apod/image/2507/test.jpg", "media_type": "image", "explanation": "Test description"}'
            ),
            (
                "GET",
                "https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos",
                {"api_key": "DEMO_KEY", "sol": 1000, "camera": "fhaz"},
                {"rover": "curiosity"},
                {},
                {},
                200,
                '{"photos": [{"id": 123, "img_src": "http://mars.jpl.nasa.gov/..."}]}'
            ),
            (
                "GET",
                "https://api.nasa.gov/neo/rest/v1/feed",
                {"api_key": "DEMO_KEY", "start_date": "2025-07-01", "end_date": "2025-07-07"},
                {},
                {},
                {},
                200,
                '{"near_earth_objects": {"2025-07-01": [{"id": "1234567", "name": "(2021 AB)", "estimated_diameter": {"meters": {"estimated_diameter_max": 100.5}}}]}}'
            ),
            (
                "POST",
                "https://jsonplaceholder.typicode.com/posts",
                {},
                {},
                {"title": "Test Post", "body": "Ceci est un test", "userId": 1},
                {"Content-Type": "application/json"},
                201,
                '{"title": "Test Post", "body": "Ceci est un test", "userId": 1, "id": 101}'
            ),
            (
                "POST",
                "https://jsonplaceholder.typicode.com/posts",
                {},
                {},
                {"invalid": "data"},
                {"Content-Type": "application/json"},
                400,
                '{"error": "Bad Request"}'
            ),
            (
                "GET",
                "https://api.nasa.gov/invalid",
                {"api_key": "DEMO_KEY"},
                {},
                {},
                {},
                404,
                '{"error": "Not found"}'
            )
        ]

        # Boucle sur chaque scénario de test
        for method, url, params, path_vars, body, headers, expected_status, expected_response in test_cases:
            # Simule la réponse de requests.request
            mock_resp = Mock()
            mock_resp.status_code = expected_status
            mock_resp.text = expected_response
            mock_request.return_value = mock_resp

            # ✅ Utilisation du préfixe /api/ car l'app est montée sous /api/
            response = self.client.post(
                '/api/test_endpoint/',
                data=json.dumps({
                    'method': method,
                    'url': url,
                    'params': params,
                    'path_vars': path_vars,
                    'body': body,
                    'headers': headers
                }),
                content_type='application/json'
            )

            # Vérifie que la vue Django a bien répondu
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['status_code'], expected_status)
            self.assertEqual(data['response'], expected_response)
            if body:
                self.assertEqual(data['request_body'], body)

    def test_download_history(self):
        # ✅ Utilisation du préfixe /api/ car l'app est montée sous /api/
        response = self.client.get('/api/download_history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertTrue(
            response.headers['Content-Disposition'].startswith('attachment; filename=test_history.json'),
            "Le header Content-Disposition doit contenir un fichier test_history.json"
        )
