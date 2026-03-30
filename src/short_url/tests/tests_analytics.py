from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
# from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from short_url.models import Click, ShortUrl

User = get_user_model()


class TestRedirect(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("generate_dummy_clicks")
        cls.user = User.objects.get(email="dummydata@gmail.com")
        cls.url = ShortUrl.objects.get(user=cls.user)

    def test_get_return_200_if_success(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("short_url_analytics", args=[self.url.id]))

        self.assertEqual(res.status_code, 200)

        data = res.json()
        self.assertEqual(data["total_clicks"], 100)
        self.assertEqual(data["unique_clicks"], 5)

        # hanya ada 1 hari dengan count = 100 clicks
        self.assertEqual(len(data["clicks_per_day"]), 1)
        self.assertEqual(data["clicks_per_day"][0]["count"], 100)

        # pastikan hanya maksimal banyak data list hanya 3
        self.assertLessEqual(len(data["top_countries"]), 3)
        self.assertLessEqual(len(data["top_referers"]), 3)
        self.assertLessEqual(len(data["top_devices"]), 3)
