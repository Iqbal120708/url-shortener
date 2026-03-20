from rest_framework.views import APIView
from .models import ShortUrl
from .serializers import ShortUrlSerializer
from .utils import generate_short_code
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache


# Create your views here.
class ShortUrlView(APIView):
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
