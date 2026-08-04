from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)

from .serializers import OTPSerializer, RegisterSerializer, ResendOTPSerializer

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
                    value={"token": "AbCdEf1234567890..."},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad Request",
            examples=[
                OpenApiExample(
                    "Email already registered",
                    value={"detail": "Email is already registered."},
                    response_only=True,
                ),
            ],
        ),
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
                    value={"message": "Account activated successfully! Please log in."},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad Request",
            examples=[
                OpenApiExample(
                    "Session expired",
                    value={"detail": "Session expired, please register again."},
                    response_only=True,
                ),
                OpenApiExample(
                    "OTP expired",
                    value={"detail": "OTP code has expired, please request a new one."},
                    response_only=True,
                ),
                OpenApiExample(
                    "OTP invalid",
                    value={"detail": "Invalid OTP code."},
                    response_only=True,
                ),
            ],
        ),
        429: OpenApiResponse(
            description="Too Many Requests",
            examples=[
                OpenApiExample(
                    "Locked out",
                    value={"detail": "Too many failed attempts. Please request a new OTP."},
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
                        "detail": "An error occurred during activation. Please try again."
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)

resend_schema = extend_schema(
    operation_id="auth_resend_otp",
    tags=["Auth"],
    summary="Resend OTP code",
    description="Resend a new OTP code to the email tied to the given token.",
    request=ResendOTPSerializer,
    responses={
        200: OpenApiResponse(description="OTP resent successfully"),
        400: OpenApiResponse(
            description="Bad Request",
            examples=[
                OpenApiExample(
                    "Missing token",
                    value={"token": ["This field is required."]},
                    response_only=True,
                ),
                OpenApiExample(
                    "Session expired",
                    value={"detail": "Session expired, please register again."},
                    response_only=True,
                ),
            ],
        ),
        429: OpenApiResponse(
            description="Too Many Requests",
            examples=[
                OpenApiExample(
                    "Cooldown active",
                    value={"detail": "Please wait 42 seconds before requesting a new OTP."},
                    response_only=True,
                ),
                OpenApiExample(
                    "Daily limit reached",
                    value={"detail": "Daily OTP request limit reached."},
                    response_only=True,
                ),
            ],
        ),
    },
)