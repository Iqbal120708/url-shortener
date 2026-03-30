from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ShortUrl(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=7, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "short_urls"

    def soft_delete(self):
        self.is_active = False
        self.save()

    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"


class Click(models.Model):
    short_url = models.ForeignKey(
        ShortUrl, on_delete=models.CASCADE, related_name="clicks"
    )
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    referer = models.URLField(max_length=2048, null=True, blank=True)
    referer_domain = models.CharField(max_length=255)
    browser = models.CharField(max_length=100, null=True, blank=True)
    os = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(max_length=50, null=True, blank=True)
    country_code = models.CharField(max_length=5, null=True, blank=True)

    class Meta:
        db_table = "clicks"
        indexes = [
            models.Index(fields=["short_url", "clicked_at", "country_code"]),
            models.Index(fields=["short_url", "clicked_at", "device_type"]),
            models.Index(fields=["short_url", "clicked_at", "referer_domain"]),
        ]

    def __str__(self):
        return f"Click on {self.short_url.short_code} at {self.clicked_at}"
