from django.urls import path

from .views import ShortUrlView

urlpatterns = [
    path("", ShortUrlView.as_view(), name="short_url"),
    path("<int:id>/", ShortUrlView.as_view(), name="short_url"),
]
