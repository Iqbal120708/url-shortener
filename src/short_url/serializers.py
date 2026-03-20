from rest_framework import serializers
from .models import ShortUrl
from .utils import generate_short_code
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException


class ShortUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortUrl
        fields = ["original_url", "short_code", "expired_at", "is_active"]
        read_only_fields = ["short_code", "expired_at", "is_active"]

    def create(self, validated_data):
        user = self.context["request"].user

        for _ in range(5):
            try:
                short_code = generate_short_code()
                with transaction.atomic():
                    return ShortUrl.objects.create(
                        user=user,
                        short_code=short_code,
                        **validated_data,
                    )
            except IntegrityError:
                continue

        raise APIException("Failed to generate short code, please try again.")
