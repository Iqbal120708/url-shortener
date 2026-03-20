from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ShortUrl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=7, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "short_urls"

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"

    @property
    def is_expired(self):
        from django.utils import timezone

        if self.expired_at is None:
            return False
        return timezone.now() > self.expired_at


class Click(models.Model):
    short_url = models.ForeignKey(
        ShortUrl, on_delete=models.CASCADE, related_name="clicks"
    )
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    referer = models.URLField(max_length=2048, null=True, blank=True)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "clicks"

    def __str__(self):
        return f"Click on {self.short_url.short_code} at {self.clicked_at}"
