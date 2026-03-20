from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APITestCase

from short_url.models import ShortUrl

User = get_user_model()


class TestCreateShortUrl(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        self.form_data = {
            "original_url": "https://www.google.com/search?q=django+rest+framework+tutorial&oq=django+rest+framework&aqs=chrome.0.69i59j69i57j69i60l3j69i65j69i60l2.2837j0j7&sourceid=chrome&ie=UTF-8"
        }

    def test_post_return_201_if_success(self):
        self.client.force_authenticate(self.user)
        self.client.credentials(
            HTTP_IDEMPOTENCY_KEY="550e8400-e29b-41d4-a716-446655440000"
        )

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")

        self.assertEqual(res.status_code, 201)
        self.assertEqual(ShortUrl.objects.count(), 1)
        self.assertTrue(res.data["short_code"])
        self.assertTrue(res.data["original_url"])
        self.assertTrue(res.data["is_active"])
        self.assertIsNone(res.data["expired_at"])

    @patch("short_url.serializers.generate_short_code")
    def test_post_return_500_if_api_except(self, mock_generate_short_code):
        short_code = "mytest1"
        ShortUrl.objects.create(
            short_code=short_code,
            original_url=self.form_data["original_url"],
            user=self.user,
        )

        mock_generate_short_code.return_value = short_code

        self.client.force_authenticate(self.user)
        self.client.credentials(
            HTTP_IDEMPOTENCY_KEY="550e8400-e29b-41d4-a716-446655440000"
        )

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")

        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.data["detail"].code, "error")
        self.assertEqual(mock_generate_short_code.call_count, 5)

    @patch("short_url.serializers.generate_short_code")
    def test_post_return_201_if_short_code_collision_on_first_attempt(
        self, mock_generate_short_code
    ):
        short_code = "mytest1"
        ShortUrl.objects.create(
            short_code=short_code,
            original_url=self.form_data["original_url"],
            user=self.user,
        )

        mock_generate_short_code.side_effect = [short_code, "abc1234"]

        self.client.force_authenticate(self.user)
        self.client.credentials(
            HTTP_IDEMPOTENCY_KEY="550e8400-e29b-41d4-a716-446655440000"
        )

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")

        self.assertEqual(res.status_code, 201)
        self.assertEqual(ShortUrl.objects.count(), 2)
        self.assertTrue(res.data["short_code"])
        self.assertTrue(res.data["original_url"])
        self.assertTrue(res.data["is_active"])
        self.assertIsNone(res.data["expired_at"])

        self.assertEqual(mock_generate_short_code.call_count, 2)

    def test_post_return_429_if_fast_repeat_request(self):
        self.client.force_authenticate(self.user)

        self.client.credentials(
            HTTP_IDEMPOTENCY_KEY="550e8400-e29b-41d4-a716-446655440000"
        )

        responses = []
        for _ in range(3):
            res = self.client.post(
                reverse("short_url"), data=self.form_data, format="json"
            )
            responses.append(res)

        self.assertEqual(responses[0].status_code, 201)
        self.assertEqual(ShortUrl.objects.count(), 1)

        self.assertEqual(responses[1].status_code, 429)
        self.assertEqual(responses[2].status_code, 429)

    def test_post_return_400_idempotency_key_does_not_exist(self):
        self.client.force_authenticate(self.user)

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["detail"], "Idempotency-Key header is required.")

    def test_post_return_400_idempotency_key_str_length_is_incorrect(self):
        self.client.force_authenticate(self.user)
        self.client.credentials(HTTP_IDEMPOTENCY_KEY="550e8400")  # key < 16

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.data["detail"], "Idempotency-Key must be between 16 and 64 characters."
        )

        self.client.credentials(
            HTTP_IDEMPOTENCY_KEY="550e8400-e29b-41d4-a716-446655440000-446655440000-446655440000-446655440000"
        )  # key > 64

        res = self.client.post(reverse("short_url"), data=self.form_data, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.data["detail"], "Idempotency-Key must be between 16 and 64 characters."
        )
