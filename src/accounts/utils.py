import json
import secrets
import time
from datetime import timedelta

import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now

from .models import OTPVerifications

r = redis.Redis.from_url(settings.REDIS_URL)

User = get_user_model()


def generate_otp(user):
    otp_code = f"{secrets.randbelow(1000000):06d}"
    token = secrets.token_urlsafe(32)

    # model dibuat dulu — cuma nyimpen hash, ini yang jadi log historis
    otp_record = OTPVerifications.objects.create(
        user=user,
        otp_hash=OTPVerifications.hash_otp(otp_code),
    )

    # Redis diisi setelah model ada — payload bawa referensi ke record-nya (record_id)
    payload = {
        "email": user.email,
        "otp": otp_code,
        "otp_created_at": time.time(),
        "record_id": otp_record.id,
    }
    r.setex(f"otp:{token}", 1800, json.dumps(payload))

    return token, otp_code  # token buat FE, otp_code buat dikirim ke email


def resend_otp(token):
    raw = r.get(f"otp:{token}")
    if not raw:
        return None  # sesi berakhir, FE arahkan register ulang

    data = json.loads(raw)
    otp_code = f"{secrets.randbelow(1000000):06d}"

    # record lama ditandai unused tetap (tidak pernah dipakai), record baru dibuat buat OTP baru ini
    user = User.objects.get(email=data["email"])
    otp_record = OTPVerifications.objects.create(
        user=user,
        otp_hash=OTPVerifications.hash_otp(otp_code),
    )

    data.update(
        {
            "otp": otp_code,
            "otp_created_at": time.time(),
            "record_id": otp_record.id,
        }
    )
    r.set(f"otp:{token}", json.dumps(data), keepttl=True)

    return otp_code


def send_otp_email(user_email, otp_code):
    subject = "Kode Verifikasi Akun"
    from_email = f"{settings.APP_NAME} <{settings.EMAIL_HOST_USER}>"
    to = [user_email]

    html_content = render_to_string("registration/otp_email.html", {"otp": otp_code})

    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
