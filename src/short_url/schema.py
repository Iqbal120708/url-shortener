from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)

from .serializers import ClickSerializer, ShortUrlSerializer

list_short_url_schema = extend_schema(
    operation_id="short_url_list",
    tags=["Short Url"],
    summary="List all short URLs",
    description="Retrieve a paginated list of all short URLs belonging to the authenticated user.",
    parameters=[
        OpenApiParameter(
            name="is_active",
            type={"type": "boolean"},
            location=OpenApiParameter.QUERY,
            description="Filter URLs by active status. If not provided, returns all URLs.",
            required=False,
        ),
        OpenApiParameter(
            name="page",
            type={"type": "integer", "minimum": 1},
            location=OpenApiParameter.QUERY,
            description="Page number for pagination.",
            required=False,
        ),
    ],
    responses={
        200: ShortUrlSerializer(many=True),
    },
    extensions={"x-paginated": True},
)

create_short_url_schema = extend_schema(
    operation_id="short_url_create",
    tags=["Short Url"],
    summary="Create data Short Url",
    parameters=[
        OpenApiParameter(
            name="Idempotency-Key",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.HEADER,
            description=(
                "Unique key to prevent duplicate requests. "
                "Must be between 16 and 64 characters. "
                "Example: my-unique-request-key-123"
            ),
            required=True,
        ),
    ],
    request=ShortUrlSerializer,
    responses={
        201: ShortUrlSerializer,
        400: OpenApiResponse(
            description="Bad Request",
            examples=[
                OpenApiExample(
                    "Idempotency-Key invalid",
                    value={
                        "detail": "Idempotency-Key must be between 16 and 64 characters."
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Idempotency-Key missing",
                    value={"detail": "Idempotency-Key header is required."},
                    response_only=True,
                ),
            ],
        ),
        429: OpenApiResponse(
            description="Too Many Requests",
            examples=[
                OpenApiExample(
                    "Idempotency-Key duplicate",
                    value={"detail": "Duplicate request ignored."},
                    response_only=True,
                )
            ],
        ),
    },
)

delete_short_url_schema = extend_schema(
    operation_id="short_url_delete",
    tags=["Short Url"],
    summary="Delete data Short Url",
    responses={
        204: None,
        404: OpenApiResponse(
            description="Not Found",
            examples=[
                OpenApiExample(
                    "Short url missing",
                    value={"detail": "Short url not found."},
                    response_only=True,
                )
            ],
        ),
    },
)

detail_short_url_schema = extend_schema(
    operation_id="short_url_detail",
    tags=["Short Url"],
    summary="Get detail data Short Url",
    responses={
        200: ShortUrlSerializer,
        404: OpenApiResponse(
            description="Not Found",
            examples=[
                OpenApiExample(
                    "Short url missing",
                    value={"detail": "Short url not found."},
                    response_only=True,
                )
            ],
        ),
    },
)

redirect_short_url_schema = extend_schema(
    operation_id="redirect",
    tags=["Redirect"],
    summary="Redirect short url to original url",
    responses={
        302: OpenApiResponse(
            description="Redirects to the original URL.",
        ),
        404: OpenApiResponse(
            description="Not Found",
            examples=[
                OpenApiExample(
                    "Short url missing",
                    value={"detail": "Short url not found."},
                    response_only=True,
                ),
                OpenApiExample(
                    "Short url is not active",
                    value={"detail": "Short url is not active."},
                    response_only=True,
                ),
            ],
        ),
    },
)

analytics_short_url_schema = extend_schema(
    operation_id="analytics",
    tags=["Analytics"],
    summary="Get data analytics short url",
    parameters=[
        OpenApiParameter(
            name="range",
            type={"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
            location=OpenApiParameter.QUERY,
            description=(
                "Filter click data for the last N days. "
                "For example, range=7 returns data from the last 7 days, "
            ),
            required=False,
        ),
        OpenApiParameter(
            name="top",
            type={"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
            location=OpenApiParameter.QUERY,
            description=(
                "Limit the number of results returned for countries, devices, and referers ranking by click count. "
                "For example, top=5 returns the top 5 of each category"
            ),
            required=False,
        ),
    ],
    responses={
        200: ClickSerializer,
        400: OpenApiResponse(
            description="Not Found",
            examples=[
                OpenApiExample(
                    "Short url missing",
                    value={"detail": "Short url not found."},
                    response_only=True,
                )
            ],
        ),
    },
)
