from drf_spectacular.utils import (OpenApiExample, OpenApiParameter,
                                   OpenApiResponse, extend_schema)

from .serializers import OTPSerializer, RegisterSerializer

register_schema = extend_schema(
    operation_id="auth_register",
    tags=["Auth"],
    summary="Register a new user",
    description="Register a new user and send an OTP code to the provided email for account verification.",
    request=RegisterSerializer,
    responses={
        200: OpenApiResponse(
            description="Registration successful",
            examples=[
                OpenApiExample(
                    "Success",
                    value={
                        "message": "Registrasi berhasil. Silakan masukkan kode otp yang dikirim ke email kamu untuk verifikasi akun."
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(description="Bad Request"),
    },
)

verify_schema = extend_schema(
    operation_id="auth_verify",
    tags=["Auth"],
    summary="Verify OTP code",
    description="Verify the OTP code sent to the user email to activate the account.",
    request=OTPSerializer,
    responses={
        200: OpenApiResponse(
            description="OTP verification successful",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"message": "Akun berhasil diaktivasi! Silakan login."},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad Request",
            examples=[
                OpenApiExample(
                    "OTP invalid",
                    value={"detail": "Kode OTP tidak valid atau sudah kadaluwarsa."},
                    response_only=True,
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Not Found",
            examples=[
                OpenApiExample(
                    "User not found",
                    value={"detail": "User not found"},
                    response_only=True,
                ),
            ],
        ),
        500: OpenApiResponse(
            description="Internal Server Error",
            examples=[
                OpenApiExample(
                    "Server error",
                    value={
                        "detail": "Terjadi kesalahan saat aktivasi. Silakan coba lagi."
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
