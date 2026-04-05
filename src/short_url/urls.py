from django.urls import path

from .views import (ClickAnalyticsView, DeleteShortUrlView, DetailShortUrlView,
                    ShortUrlView)

urlpatterns = [
    path("", ShortUrlView.as_view(), name="short_url"),
    path("<int:id>/", DeleteShortUrlView.as_view(), name="short_url"),
    path(
        "<str:short_code>/detail/",
        DetailShortUrlView.as_view(),
        name="detail_short_url",
    ),
    path(
        "<int:short_url_id>/analytics/",
        ClickAnalyticsView.as_view(),
        name="short_url_analytics",
    ),
]
