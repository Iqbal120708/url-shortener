from unittest.mock import patch

import fakeredis
from django.contrib.auth import get_user_model
from django.urls import reverse
from freezegun import freeze_time
from rest_framework.test import APITestCase

from accounts.models import OTPVerifications

User = get_user_model()

fake_redis = fakeredis.FakeStrictRedis()


@freeze_time("2026-02-24 10:00:00")
@patch("accounts.views.r", fake_redis)
@patch("accounts.utils.r", fake_redis)
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

    def setUp(self):
        fake_redis.flushall()

    def test_user_already_registered(self):
        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["email"][0], "Email is already registered.")
        self.assertEqual(res.data["email"][0].code, "unique")

    def test_password_does_not_match(self):
        self.form_data["password2"] = "secretnotmatch"

        res = self.client.post(reverse("register"), data=self.form_data)
        self.assertEqual(res.status_code, 400)

    @patch("accounts.views.send_otp_email")
    def test_user_exists_and_not_active(self, mock_send_email):
        self.user.is_active = False
        self.user.save()

        old_first_name = self.user.first_name
        old_last_name = self.user.last_name
        old_password = self.user.password

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 200)
        self.assertIn("token", res.data)

        self.assertEqual(OTPVerifications.objects.count(), 1)

        instance_otp = OTPVerifications.objects.filter(user=self.user).first()
        self.assertTrue(instance_otp)
        self.assertIsNone(instance_otp.used_at)

        sent_email, sent_otp_code = mock_send_email.call_args[0]
        self.assertEqual(sent_email, self.user.email)
        self.assertEqual(OTPVerifications.hash_otp(sent_otp_code), instance_otp.otp_hash)

        raw = fake_redis.get(f"otp:{res.data['token']}")
        self.assertIsNotNone(raw)

        self.user.refresh_from_db()

        self.assertNotEqual(self.user.first_name, old_first_name)
        self.assertNotEqual(self.user.last_name, old_last_name)
        self.assertFalse(self.user.check_password(old_password))

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
        self.assertIn("token", res.data)

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
        self.assertIsNone(instance_otp.used_at)

        sent_email, sent_otp_code = mock_send_email.call_args[0]
        self.assertEqual(sent_email, "test2@gmail.com")
        self.assertEqual(OTPVerifications.hash_otp(sent_otp_code), instance_otp.otp_hash)

        raw = fake_redis.get(f"otp:{res.data['token']}")
        self.assertIsNotNone(raw)

    @patch("accounts.views.send_otp_email")
    def test_register_count_limit_reached(self, mock_send_email):
        self.form_data["first_name"] = "fiesta"
        self.form_data["last_name"] = "dma"
        self.form_data["email"] = "test2@gmail.com"
        
        # simulasikan sudah 5x register untuk email ini dalam window 3 jam
        fake_redis.set(f"register_count:{self.form_data['email']}", 5)

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 429)
        mock_send_email.assert_not_called()

    @patch("accounts.views.send_otp_email")
    def test_register_count_resets_after_window(self, mock_send_email):
        self.user.is_active = False
        self.user.save()

        # simulasikan window 3 jam sudah lewat: counter sudah tidak ada
        fake_redis.delete(f"register_count:{self.form_data['email']}")

        res = self.client.post(reverse("register"), data=self.form_data)

        self.assertEqual(res.status_code, 200)
        count = int(fake_redis.get(f"register_count:{self.form_data['email']}"))
        self.assertEqual(count, 1)