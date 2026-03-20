from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from accounts.models import OTPVerifications

User = get_user_model()


class TestRegister(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="test", email="test@gmail.com", password="secret123"
        )

        cls.form_data = {
            "username": "test",
            "email": "test@gmail.com",
            "password1": "secret123",
            "password2": "secret123",
        }

    def test_user_already_registered(self):
        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["username"][0].code, "unique")
        self.assertEqual(res.data["email"][0].code, "unique")

    @patch("accounts.views.send_otp_email")
    def test_user_exists_and_not_active(self, mock_send_email):
        self.user.is_active = False
        self.user.save()

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["message"],
            "Registrasi berhasil. Silakan masukkan kode otp yang dikirim ke email kamu untuk verifikasi akun.",
        )

        self.assertEqual(OTPVerifications.objects.count(), 1)

        instance_otp = OTPVerifications.objects.filter(user=self.user).first()
        self.assertTrue(instance_otp)

        mock_send_email.assert_called_once_with(self.user.email, instance_otp.otp)

    @patch("accounts.views.send_otp_email")
    def test_success(self, mock_send_email):
        self.form_data["username"] = "test2"
        self.form_data["email"] = "test2@gmail.com"

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["message"],
            "Registrasi berhasil. Silakan masukkan kode otp yang dikirim ke email kamu untuk verifikasi akun.",
        )

        # results by setup and new res data
        self.assertEqual(User.objects.count(), 2)
        self.assertFalse(User.objects.get(username="test2").is_active)

        self.assertEqual(OTPVerifications.objects.count(), 1)

        instance_otp = OTPVerifications.objects.filter(
            user__email="test2@gmail.com"
        ).first()
        self.assertTrue(instance_otp)

        mock_send_email.assert_called_once_with("test2@gmail.com", instance_otp.otp)
