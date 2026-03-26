from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from short_url.models import ShortUrl
from short_url.utils import generate_short_code

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestGetList(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        data = [
            ShortUrl(
                original_url="https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
                short_code=generate_short_code(),
                user=self.user,
            )
            for _ in range(200)
        ]
        ShortUrl.objects.bulk_create(data)

    def test_get_return_200_if_success(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("short_url"))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 200)
        self.assertEqual(len(res.data["results"]), 100)
        self.assertIsNone(res.data["previous"])

    def test_get_page2_return_200_if_success(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(f'{reverse("short_url")}?page=2')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["count"], 200)
        self.assertEqual(len(res.data["results"]), 100)
        self.assertIsNone(res.data["next"])
