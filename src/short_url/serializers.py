from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import ShortUrl
from .utils import generate_short_code


class ShortUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortUrl
        fields = ["id", "original_url", "short_code", "is_active"]
        read_only_fields = ["short_code", "is_active"]

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
