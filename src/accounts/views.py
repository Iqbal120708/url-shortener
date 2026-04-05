from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import render
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.json_resp import res_error

from .models import OTPVerifications
from .schema import register_schema, verify_schema
from .serializers import OTPSerializer, RegisterSerializer
from .utils import generate_otp, send_otp_email

User = get_user_model()


# Create your views here.
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @register_schema
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email=serializer.validated_data["email"]).first()
        if not user:
            user = serializer.save()

        otp_code = generate_otp(user)
        send_otp_email(user.email, otp_code)

        return Response(
            {
                "message": "Registrasi berhasil. Silakan masukkan kode otp yang dikirim ke email kamu untuk verifikasi akun."
            },
            status=status.HTTP_200_OK,
        )


class VerifyView(APIView):
    permission_classes = [AllowAny]

    @verify_schema
    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()
        if not user:
            return res_error("User not found", status.HTTP_404_NOT_FOUND)

        otp_code = serializer.validated_data["otp_code"]
        latest_otp = (
            OTPVerifications.objects.filter(
                user__email=email,
                otp=otp_code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if latest_otp and latest_otp.created_at <= now() <= latest_otp.expired_at:
            try:
                with transaction.atomic():
                    latest_otp.is_used = True
                    latest_otp.save()

                    user = latest_otp.user
                    user.is_active = True
                    user.save()
            except Exception as e:
                exc = APIException(
                    "Terjadi kesalahan saat aktivasi. Silakan coba lagi."
                )
                raise exc
        else:
            return res_error(
                "Kode OTP tidak valid atau sudah kadaluwarsa.",
                status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Akun berhasil diaktivasi! Silakan login."},
            status=status.HTTP_200_OK,
        )
