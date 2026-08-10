import json
import time
from unittest.mock import patch

import fakeredis
from django.contrib.auth import get_user_model
from django.urls import reverse
from freezegun import freeze_time
from rest_framework.test import APITestCase

from accounts.models import OTPVerifications

fake_redis = fakeredis.FakeStrictRedis()


def _seed_otp_session(user, otp_code="123456", created_offset=0):
    otp_record = OTPVerifications.objects.create(
        user=user,
        otp_hash=OTPVerifications.hash_otp(otp_code),
    )
    token = "test-token-abc123"
    payload = {
        "email": user.email,
        "otp": otp_code,
        "otp_created_at": time.time() - created_offset,
        "record_id": otp_record.id,
    }
    fake_redis.setex(f"otp:{token}", 1800, json.dumps(payload))
    return token, otp_record


@freeze_time("2026-02-24 10:00:00")
@patch("accounts.views.r", fake_redis)
@patch("accounts.utils.r", fake_redis)
@patch("accounts.views.send_otp_email.delay")
class TestResendOTP(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            first_name="first",
            last_name="last",
            email="test@gmail.com",
            password="secret123",
            is_active=False,
        )

    def setUp(self):
        fake_redis.flushall()
        self.token, self.otp_record = _seed_otp_session(self.user)

    def test_token_not_found(self, mock_send_email):
        res = self.client.post(
            reverse("resend_otp"),
            data={"token": "nonexistent-token"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["detail"], "Session expired, please register again.")
        mock_send_email.assert_not_called()

    def test_success(self, mock_send_email):
        res = self.client.post(reverse("resend_otp"), data={"token": self.token})

        self.assertEqual(res.status_code, 200)

        raw = fake_redis.get(f"otp:{self.token}")
        data = json.loads(raw)

        # OTP baru terkirim dengan kode yang cocok dengan yang tersimpan di Redis
        mock_send_email.assert_called_once_with(self.user.email, data["otp"])

        # record baru dibuat, record_id di payload ikut update
        self.assertNotEqual(data["record_id"], self.otp_record.id)
        self.assertTrue(OTPVerifications.objects.filter(id=data["record_id"]).exists())

        # otp_created_at ter-update jadi "sekarang"
        self.assertAlmostEqual(data["otp_created_at"], time.time(), delta=1)

    def test_ttl_not_reset_keepttl(self, mock_send_email):
        # sesi sudah berjalan 1000 detik dari TTL awal 1800 detik
        fake_redis.expire(f"otp:{self.token}", 800)  # sisa 800 detik (contoh)
        ttl_before = fake_redis.ttl(f"otp:{self.token}")

        self.client.post(reverse("resend_otp"), data={"token": self.token})

        ttl_after = fake_redis.ttl(f"otp:{self.token}")
        # TTL tidak direset ke 1800 lagi, tetap sekitar sisa waktu sebelumnya
        self.assertLessEqual(ttl_after, ttl_before)

    def test_cooldown_blocks_immediate_resend(self, mock_send_email):
        self.client.post(reverse("resend_otp"), data={"token": self.token})
        mock_send_email.reset_mock()

        res = self.client.post(reverse("resend_otp"), data={"token": self.token})

        self.assertEqual(res.status_code, 429)
        self.assertIn("wait", res.data["detail"].lower())
        mock_send_email.assert_not_called()

    def test_resend_allowed_after_cooldown_expires(self, mock_send_email):
        self.client.post(reverse("resend_otp"), data={"token": self.token})

        with freeze_time("2026-02-24 10:01:01"):  # +61 detik, lewat cooldown 60 detik
            res = self.client.post(reverse("resend_otp"), data={"token": self.token})

        self.assertEqual(res.status_code, 200)
