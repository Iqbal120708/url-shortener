import warnings

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth import get_user_model
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email=email, password=password, **extra_fields)


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def soft_delete(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def hard_delete(self):
        return super().delete()

    def delete(self, *args, **kwargs):
        raise RuntimeError(_("Gunakan soft_delete() atau hard_delete()"))


class OTPVerifications(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField()
    expired_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def clean(self):
        if self.otp and not self.otp.isdigit():
            raise ValidationError({"otp": _("Kode OTP harus berupa angka.")})

        if self.created_at and self.expired_at:
            if self.created_at > self.expired_at:
                raise ValidationError(
                    _("Waktu kedaluwarsa tidak boleh lebih awal dari waktu pembuatan.")
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.otp} - {self.is_used}"
