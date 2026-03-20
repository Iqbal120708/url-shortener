from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework.test import APITestCase

from accounts.models import OTPVerifications


@freeze_time("2026-02-24 10:00:00")
class TestVerifyOTP(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="test",
            email="test@gmail.com",
            password="secret123",
            is_active=False,
        )

        created_at = now()
        expired_at = created_at + timedelta(minutes=5)

        cls.otp = OTPVerifications.objects.create(
            user=cls.user,
            otp="123456",
            created_at=created_at,
            expired_at=expired_at,
        )

    def test_otp_invalid(self):
        res = self.client.post(
            reverse("verify_otp"),
            data={"email": "test@gmail.com", "otp_code": "abcdef"},
        )

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["otp_code"][0], "OTP harus berupa angka")

    @freeze_time("2026-02-24 11:00:00")
    def test_otp_expired(self):
        res = self.client.post(
            reverse("verify_otp"), data={"email": self.user.email, "otp_code": "123456"}
        )

        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.data["detail"], "Kode OTP tidak valid atau sudah kadaluwarsa."
        )

    @patch("accounts.views.User.save")
    def test_error_transaction_db(self, mock_save):
        mock_save.side_effect = Exception("DB error")

        res = self.client.post(
            reverse("verify_otp"), data={"email": self.user.email, "otp_code": "123456"}
        )

        self.assertEqual(res.status_code, 500)
        self.assertEqual(
            res.data["detail"], "Terjadi kesalahan saat aktivasi. Silakan coba lagi."
        )

        # pastikan ke rollback
        self.otp.refresh_from_db()
        self.assertFalse(self.otp.is_used)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_success(self):
        session = self.client.session
        session["pending_user_email"] = self.user.email
        session.save()

        res = self.client.post(
            reverse("verify_otp"), data={"email": self.user.email, "otp_code": "123456"}
        )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["message"], "Akun berhasil diaktivasi! Silakan login."
        )

        self.otp.refresh_from_db()
        self.assertTrue(self.otp.is_used)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
