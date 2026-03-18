import secrets
import string
from .models import OTPVerifications
from django.utils.timezone import now
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def generate_otp(user, length=6):
    characters = string.digits
    otp = ''.join(secrets.choice(characters) for _ in range(length))
    
    # OTPVerifications.objects.filter(user=user, is_used=False).update(is_used=True)
    
    created_at = now()
    expired_at = created_at + timedelta(minutes=5)
    OTPVerifications.objects.create(
        user=user,
        otp=otp,
        created_at=created_at,
        expired_at=expired_at,
    )
    
    return otp

def send_otp_email(user_email, otp_code):
    subject = 'Kode Verifikasi Akun'
    from_email = f"{settings.APP_NAME} <{settings.EMAIL_HOST_USER}>"
    to = [user_email]

    html_content = render_to_string('registration/otp_email.html', {'otp': otp_code})
    
    text_content = strip_tags(html_content) 

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

