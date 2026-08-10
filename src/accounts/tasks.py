from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now

@shared_task
def send_otp_email(user_email, otp_code):
    subject = "Kode Verifikasi Akun"
    from_email = f"{settings.APP_NAME} <{settings.EMAIL_HOST_USER}>"
    to = [user_email]

    html_content = render_to_string("registration/otp_email.html", {"otp": otp_code})

    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
