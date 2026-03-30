from django.db import IntegrityError, transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import Click, ShortUrl
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


class ClickSerializer(serializers.Serializer):
    short_code = serializers.SerializerMethodField()
    original_url = serializers.SerializerMethodField()
    total_clicks = serializers.SerializerMethodField()
    unique_clicks = serializers.SerializerMethodField()
    clicks_per_day = serializers.SerializerMethodField()
    top_countries = serializers.SerializerMethodField()
    top_devices = serializers.SerializerMethodField()
    top_referers = serializers.SerializerMethodField()

    def get_short_code(self, obj):
        short_url = self.context.get("short_url")
        return short_url.short_code

    def get_original_url(self, obj):
        short_url = self.context.get("short_url")
        return short_url.original_url

    def get_total_clicks(self, obj):
        return obj.count()

    def get_unique_clicks(self, obj):
        return obj.aggregate(unique_clicks=Count("ip_address", distinct=True))[
            "unique_clicks"
        ]

    def get_clicks_per_day(self, obj):
        return (
            obj.annotate(date=TruncDate("clicked_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("-date")
        )

    def get_top_countries(self, obj):
        top = self.context.get("top")
        return (
            obj.values("country_code")
            .annotate(count=Count("id"))
            .order_by("-count")[:top]
        )

    def get_top_devices(self, obj):
        top = self.context.get("top")
        return (
            obj.values("device_type")
            .annotate(count=Count("id"))
            .order_by("-count")[:top]
        )

    def get_top_referers(self, obj):
        top = self.context.get("top")
        return (
            obj.values("referer_domain")
            .annotate(count=Count("id"))
            .order_by("-count")[:top]
        )
