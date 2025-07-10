from django.test import TestCase
from django.urls import reverse

class ProductAPITest(TestCase):
    def test_products_endpoint(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertIn('name', data[0])
