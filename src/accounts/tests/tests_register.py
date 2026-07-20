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
            email="test@gmail.com",
            password="secret123",
            first_name="old",
            last_name="name",
        )

        cls.form_data = {
            "first_name": "test",
            "last_name": "form",
            "email": "test@gmail.com",
            "password1": "secret1234",
            "password2": "secret1234",
        }

    def test_user_already_registered(self):
        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["email"][0].code, "unique")

    @patch("accounts.views.send_otp_email")
    def test_user_exists_and_not_active(self, mock_send_email):
        self.user.is_active = False
        self.user.save()

        old_first_name = self.user.first_name
        old_last_name = self.user.last_name
        old_password = self.user.password

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

        self.user.refresh_from_db()

        # pastikan data user berubah dari data lama
        self.assertNotEqual(self.user.first_name, old_first_name)
        self.assertNotEqual(self.user.last_name, old_last_name)
        self.assertFalse(self.user.check_password(old_password))

        # dan sesuai dengan form_data yang baru dikirim
        self.assertEqual(self.user.first_name, self.form_data["first_name"])
        self.assertEqual(self.user.last_name, self.form_data["last_name"])
        self.assertTrue(self.user.check_password(self.form_data["password1"]))

    @patch("accounts.views.send_otp_email")
    def test_success(self, mock_send_email):
        self.form_data["first_name"] = "fiesta"
        self.form_data["last_name"] = "dma"
        self.form_data["email"] = "test2@gmail.com"

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.data["message"],
            "Registrasi berhasil. Silakan masukkan kode otp yang dikirim ke email kamu untuk verifikasi akun.",
        )

        # results by setup and new res data
        self.assertEqual(User.objects.count(), 2)

        new_user = User.objects.get(email="test2@gmail.com")
        self.assertFalse(new_user.is_active)
        self.assertEqual(new_user.first_name, "fiesta")
        self.assertEqual(new_user.last_name, "dma")

        self.assertEqual(OTPVerifications.objects.count(), 1)

        instance_otp = OTPVerifications.objects.filter(
            user__email="test2@gmail.com"
        ).first()
        self.assertTrue(instance_otp)

        mock_send_email.assert_called_once_with("test2@gmail.com", instance_otp.otp)
