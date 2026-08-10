from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from config.json_resp import res_error
import json
import time
from .models import OTPVerifications
from .schema import register_schema, verify_schema, resend_schema
from .serializers import OTPSerializer, RegisterSerializer, ResendOTPSerializer
from .utils import generate_otp, resend_otp
from .tasks import send_otp_email
import redis

r = redis.Redis.from_url(settings.REDIS_URL)

User = get_user_model()


# Create your views here.
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @register_schema
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if user and not user.is_active:
            user = serializer.update(user, serializer.validated_data)
        elif not user:
            user = serializer.save()
        
        count_key = f"register_count:{user.email}"
        count = r.incr(count_key)
        if count == 1:
            r.expire(count_key, 10800)  # window 3 jam
        if count > 5:
            return res_error(
                "Too many registration attempts. Please try again later.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )
    
        token, otp_code = generate_otp(user)
        send_otp_email.delay(user.email, otp_code)

        return Response({"token": token}, status=status.HTTP_200_OK)
        
class VerifyView(APIView):
    permission_classes = [AllowAny]

    @verify_schema
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        otp_code_input = serializer.validated_data["otp_code"]

        raw = r.get(f"otp:{token}")
        if not raw:
            return res_error(
                "Session expired, please register again.", status.HTTP_400_BAD_REQUEST
            )

        attempt_key = f"otp_attempt:{token}"
        attempts = int(r.get(attempt_key) or 0)
        if attempts >= 5:
            r.delete(f"otp:{token}")  # invalidate sesi, paksa user minta OTP baru
            return res_error(
                "Too many failed attempts. Please request a new OTP.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        data = json.loads(raw)

        if time.time() - data["otp_created_at"] > 300:
            return res_error(
                "OTP code has expired, please request a new one.",
                status.HTTP_400_BAD_REQUEST,
            )

        if data["otp"] != otp_code_input:
            pipe = r.pipeline()
            pipe.incr(attempt_key)
            pipe.expire(attempt_key, 300)  # ikut umur OTP, bukan lebih lama
            pipe.execute()
            return res_error("Invalid OTP code.", status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=data["email"]).first()
        if not user:
            return res_error("Invalid OTP code.", status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                OTPVerifications.objects.filter(id=data["record_id"]).update(
                    used_at=now()
                )
                user.is_active = True
                user.save()
        except Exception as e:
            raise APIException(
                "An error occurred during activation. Please try again."
            ) from e

        r.delete(f"otp:{token}")
        r.delete(attempt_key)

        return Response(
            {"message": "Account activated successfully! Please log in."},
            status=status.HTTP_200_OK,
        )

class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    @resend_schema
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]

        raw = r.get(f"otp:{token}")
        if not raw:
            return res_error(
                "Session expired, please register again.", status.HTTP_400_BAD_REQUEST
            )

        data = json.loads(raw)
        email = data["email"]

        cooldown_key = f"otp_cooldown:{email}"
        if r.exists(cooldown_key):
            ttl = r.ttl(cooldown_key)
            return res_error(
                f"Please wait {ttl} seconds before requesting a new OTP.",
                status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp_code = resend_otp(token)
        if not otp_code:
            return res_error(
                "Session expired, please register again.", status.HTTP_400_BAD_REQUEST
            )

        r.setex(cooldown_key, 60, 1)
        send_otp_email.delay(email, otp_code)

        return Response(status=status.HTTP_200_OK)