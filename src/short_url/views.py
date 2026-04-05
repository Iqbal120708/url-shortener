from datetime import timedelta

from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.json_resp import res_error

from .models import Click, ShortUrl
from .schema import (
    analytics_short_url_schema,
    create_short_url_schema,
    delete_short_url_schema,
    detail_short_url_schema,
    list_short_url_schema,
    redirect_short_url_schema,
)
from .serializers import ClickSerializer, ShortUrlSerializer
from .tasks import track_click
from .utils import generate_short_code, get_client_ip


# Create your views here.
class ShortUrlView(APIView):
    @list_short_url_schema
    def get(self, request):
        extra_filter = {}

        is_active = request.GET.get("is_active")
        if is_active is not None:
            extra_filter["is_active"] = is_active.lower() == "true"

        qs = (
            ShortUrl.objects.only("id", "short_code", "original_url", "is_active")
            .filter(user=request.user, **extra_filter)
            .order_by("-id")
        )

        paginator = PageNumberPagination()
        paginator.page_size = 100
        result = paginator.paginate_queryset(qs, request)

        serializer = ShortUrlSerializer(result, many=True)
        return paginator.get_paginated_response(serializer.data)

    @create_short_url_schema
    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {"detail": "Idempotency-Key header is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(idempotency_key) < 16 or len(idempotency_key) > 64:
            return Response(
                {"detail": "Idempotency-Key must be between 16 and 64 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inserted = cache.add(f"idempotency:{idempotency_key}", True, timeout=60)
        if not inserted:
            return Response(
                {"detail": "Duplicate request ignored."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = ShortUrlSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DeleteShortUrlView(APIView):
    @delete_short_url_schema
    def delete(self, request, id):
        short_url = ShortUrl.objects.filter(id=id).first()
        if not short_url:
            return res_error("Short url not found.", status.HTTP_404_NOT_FOUND)
        if not short_url.is_active:
            return Response(status=status.HTTP_204_NO_CONTENT)

        short_url.soft_delete()

        cache.set(
            f"shorturl:{short_url.short_code}",
            {
                "id": short_url.id,
                "original_url": short_url.original_url,
                "is_active": short_url.is_active,
            },
            timeout=60 * 60 * 24,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class DetailShortUrlView(APIView):
    @detail_short_url_schema
    def get(self, request, short_code):
        short_url = (
            ShortUrl.objects.only("id", "short_code", "original_url", "is_active")
            .filter(user=request.user, short_code=short_code)
            .order_by("-id")
            .first()
        )

        if not short_url:
            return res_error("Short url not found.", status.HTTP_404_NOT_FOUND)

        serializer = ShortUrlSerializer(short_url)
        return Response(serializer.data)


class RedirectToOriginal(APIView):
    permission_classes = [AllowAny]

    @redirect_short_url_schema
    def get(self, request, short_code):
        short_url = cache.get(f"shorturl:{short_code}")
        if short_url:
            id = short_url["id"]
            original_url = short_url["original_url"]
            is_active = short_url["is_active"]

        else:
            short_url = (
                ShortUrl.objects.only("id", "short_code", "original_url", "is_active")
                .filter(short_code=short_code)
                .first()
            )
            if not short_url:
                return res_error("Short url not found.", status.HTTP_404_NOT_FOUND)

            id = short_url.id
            original_url = short_url.original_url
            is_active = short_url.is_active

            cache.set(
                f"shorturl:{short_url.short_code}",
                {"id": id, "original_url": original_url, "is_active": is_active},
                timeout=60 * 60 * 24,
            )

        if not is_active:
            return res_error("Short url is not active.", status.HTTP_404_NOT_FOUND)

        ip_address = get_client_ip(request)
        referer = request.META.get("HTTP_REFERER")
        user_agent = request.META.get("HTTP_USER_AGENT")
        track_click.delay(
            short_url_id=id,
            ip_address=ip_address,
            referer=referer,
            user_agent=user_agent,
        )

        return HttpResponseRedirect(original_url)


class ClickAnalyticsView(APIView):
    @analytics_short_url_schema
    def get(self, request, short_url_id):
        try:
            range = int(request.GET.get("range", 7))
            if range <= 0:
                range = 1
            elif range > 90:
                range = 90
        except ValueError:
            range = 7

        try:
            top = int(request.GET.get("top", 3))
            if top <= 0:
                top = 1
            elif top > 10:
                top = 10
        except ValueError:
            top = 3

        short_url = ShortUrl.objects.filter(user=request.user, id=short_url_id).first()
        if not short_url:
            return res_error("Short url not found.", status.HTTP_404_NOT_FOUND)

        range_time = timezone.now() - timedelta(days=range)
        clicks = Click.objects.filter(short_url=short_url, clicked_at__gte=range_time)

        serializer = ClickSerializer(
            clicks, context={"top": top, "short_url": short_url}
        )
        return Response(serializer.data)
