from django.urls import path

from .views import DetailShortUrlView, ShortUrlView

urlpatterns = [
    path("", ShortUrlView.as_view(), name="short_url"),
    path("<int:id>/", ShortUrlView.as_view(), name="short_url"),
    path(
        "<str:short_code>/detail/",
        DetailShortUrlView.as_view(),
        name="detail_short_url",
    ),
]
