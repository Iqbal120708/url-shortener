from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from short_url.models import Click, ShortUrl

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestRedirect(TransactionTestCase):
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

    def make_request(self):
        try:
            return self.client.get(reverse("redirect_to_original", args=["abc1234"]))
        finally:
            connection.close()

    @patch("short_url.views.cache.set")
    def test_redirect_return_302_if_from_database(self, mock_cache_set):
        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))

        queries = [q["sql"] for q in ctx.captured_queries]
        table_name = ShortUrl._meta.db_table
        shorturl_queries = [q for q in queries if table_name in q]

        # query runs in track_click task and view
        self.assertEqual(len(shorturl_queries), 2)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(
            res["Location"],
            "https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
        )

        mock_cache_set.assert_called_once_with(
            "shorturl:abc1234",
            {
                "id": 1,
                "original_url": "https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
                "is_active": True,
            },
            timeout=60 * 60 * 24,
        )

        self.assertEqual(Click.objects.count(), 1)

    @patch("short_url.views.cache.get")
    @patch("short_url.views.cache.set")
    def test_redirect_return_302_if_from_cache(self, mock_cache_set, mock_cache_get):
        mock_cache_get.return_value = {
            "id": self.url.id,
            "original_url": self.url.original_url,
            "is_active": self.url.is_active,
        }

        with CaptureQueriesContext(connection) as ctx:
            res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))

        queries = [q["sql"] for q in ctx.captured_queries]
        table_name = ShortUrl._meta.db_table
        shorturl_queries = [q for q in queries if table_name in q]

        # query runs in track_click task
        self.assertEqual(len(shorturl_queries), 1)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(
            res["Location"],
            "https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
        )

        mock_cache_set.assert_not_called()
        mock_cache_get.assert_called_once_with("shorturl:abc1234")

        self.assertEqual(Click.objects.count(), 1)

    def test_redirect_return_404_if_short_url_not_found(self):
        res = self.client.get(reverse("redirect_to_original", args=["0000000"]))

        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["detail"], "Short url not found.")

    def test_redirect_return_404_if_short_url_is_not_active(self):
        self.url.is_active = False
        self.url.save()

        res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))

        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["detail"], "Short url is not active.")

    @patch("short_url.views.cache.get")
    def test_redirect_return_404_if_cache_short_url_is_not_active(self, mock_cache_get):
        mock_cache_get.return_value = {
            "id": self.url.id,
            "original_url": self.url.original_url,
            "is_active": False,
        }

        res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))

        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["detail"], "Short url is not active.")

        mock_cache_get.assert_called_once_with("shorturl:abc1234")
