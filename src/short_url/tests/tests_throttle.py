from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from short_url.models import ShortUrl

User = get_user_model()


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "throttle-test",
        }
    }
)
class ThrottleTest(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        self.url = ShortUrl.objects.create(
            original_url="https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8",
            short_code="abc1234",
            user=self.user,
        )

    def test_anon_throttle(self):
        for i in range(60):
            res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))
            self.assertEqual(res.status_code, 302)

        # 61st request should be throttled
        res = self.client.get(reverse("redirect_to_original", args=["abc1234"]))
        self.assertEqual(res.status_code, 429)
