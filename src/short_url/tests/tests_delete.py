from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from short_url.models import ShortUrl

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TestRedirect(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        self.url = ShortUrl.objects.create(
            original_url="https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
            short_code="abc1234",
            user=self.user,
        )

    @patch("short_url.views.cache.set")
    def test_delete_return_204_if_success(self, mock_cache_set):
        self.client.force_authenticate(self.user)
        self.assertTrue(self.url.is_active)  # before delete

        res = self.client.delete(reverse("short_url", args=[self.url.id]))

        self.assertEqual(res.status_code, 204)

        self.url.refresh_from_db()
        self.assertFalse(self.url.is_active)  # after delete

        mock_cache_set.assert_called_once_with(
            "shorturl:abc1234",
            {
                "id": 1,
                "original_url": "https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
                "is_active": False,
            },
            timeout=60 * 60 * 24,
        )  # check is_active = False.

    def test_delete_return_404_if_short_url_not_found(self):
        self.client.force_authenticate(self.user)

        res = self.client.delete(reverse("short_url", args=[999]))

        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.data["detail"], "Short url not found.")

    def test_short_url_cannot_be_used_after_delete(self):
        self.client.force_authenticate(self.user)

        # redirect before delete
        res_redirect = self.client.get(
            reverse("redirect_to_original", args=[self.url.short_code])
        )

        # check redirect success before delete
        self.assertEqual(res_redirect.status_code, 302)

        res = self.client.delete(reverse("short_url", args=[self.url.id]))
        self.assertEqual(res.status_code, 204)

        # redirect after delete
        res_redirect = self.client.get(
            reverse("redirect_to_original", args=[self.url.short_code])
        )

        # check redirect success after delete
        self.assertEqual(res_redirect.status_code, 404)
        self.assertEqual(res_redirect.data["detail"], "Short url is not active.")
