from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(label="Password Confirm", write_only=True)
    username = serializers.CharField(max_length=255)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "password1",
            "password2",
        ]

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError("Password tidak cocok.")
        return attrs

    def validate_username(self, value):
        user = User.objects.filter(username=value).first()

        if user and user.is_active:
            raise serializers.ValidationError(
                "Username already registered.", code="unique"
            )

        return value

    def validate_email(self, value):
        user = User.objects.filter(email=value).first()

        if user and user.is_active:
            raise serializers.ValidationError(
                "Email already registered.", code="unique"
            )

        return value

    def create(self, validated_data):
        validated_data.pop("password2")
        validated_data["password"] = validated_data.pop("password1")
        user = User.objects.create_user(is_active=False, **validated_data)
        return user


class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP harus berupa angka")

        return value
