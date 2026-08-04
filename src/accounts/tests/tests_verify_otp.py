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
    """Helper: buat record OTP di DB + isi Redis, mirip generate_otp() tapi untuk setup test."""
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
class TestVerifyOTP(APITestCase):
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

    def test_otp_invalid_format(self):
        res = self.client.post(
            reverse("verify_otp"),
            data={"token": self.token, "otp_code": "abcdef"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["otp_code"][0], "OTP code must be numeric.")

    def test_token_not_found(self):
        res = self.client.post(
            reverse("verify_otp"),
            data={"token": "nonexistent-token", "otp_code": "123456"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["detail"], "Session expired, please register again.")

    def test_otp_expired(self):
        # timpa payload dengan otp_created_at 301 detik lalu (lewat batas 300 detik)
        expired_token, _ = _seed_otp_session(self.user, created_offset=301)
        res = self.client.post(
            reverse("verify_otp"),
            data={"token": expired_token, "otp_code": "123456"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.data["detail"], "OTP code has expired, please request a new one."
        )

    def test_otp_wrong_code_increments_attempt(self):
        res = self.client.post(
            reverse("verify_otp"),
            data={"token": self.token, "otp_code": "999999"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["detail"], "Invalid OTP code.")
        self.assertEqual(int(fake_redis.get(f"otp_attempt:{self.token}")), 1)

    def test_lockout_after_five_failed_attempts(self):
        for _ in range(5):
            self.client.post(
                reverse("verify_otp"),
                data={"token": self.token, "otp_code": "999999"},
            )

        res = self.client.post(
            reverse("verify_otp"),
            data={
                "token": self.token,
                "otp_code": "123456",
            },  # kode benar, tapi sudah lockout
        )
        self.assertEqual(res.status_code, 429)
        self.assertEqual(
            res.data["detail"], "Too many failed attempts. Please request a new OTP."
        )
        # sesi harus sudah diinvalidate
        self.assertIsNone(fake_redis.get(f"otp:{self.token}"))

    @patch("accounts.views.User.save")
    def test_error_transaction_db(self, mock_save):
        mock_save.side_effect = Exception("DB error")

        res = self.client.post(
            reverse("verify_otp"),
            data={"token": self.token, "otp_code": "123456"},
        )

        self.assertEqual(res.status_code, 500)
        self.assertEqual(
            res.data["detail"], "An error occurred during activation. Please try again."
        )

        self.otp_record.refresh_from_db()
        self.assertIsNone(self.otp_record.used_at)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_success(self):
        res = self.client.post(
            reverse("verify_otp"),
            data={"token": self.token, "otp_code": "123456"},
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["message"], "Account activated successfully! Please log in."
        )

        self.otp_record.refresh_from_db()
        self.assertIsNotNone(self.otp_record.used_at)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

        # sesi & attempt counter harus dihapus setelah sukses
        self.assertIsNone(fake_redis.get(f"otp:{self.token}"))
        self.assertIsNone(fake_redis.get(f"otp_attempt:{self.token}"))
