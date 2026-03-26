from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from short_url.models import ShortUrl

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestDelete(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        self.url = ShortUrl.objects.create(
            original_url="https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
            short_code="abc1234",
            user=self.user,
        )

    def test_get_return_200_if_success(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("detail_short_url", args=["abc1234"]))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["short_code"], "abc1234")

    def test_get_return_404_if_not_found(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(reverse("detail_short_url", args=["1234abc"]))

        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["detail"], "Short url not found.")
