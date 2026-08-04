import warnings
import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUserQuerySet(models.QuerySet):
    def delete(self):
        raise RuntimeError("Gunakan soft_delete() atau hard_delete() per instance")

    def soft_delete(self):
        return self.update(is_active=False)

    def hard_delete(self):
        return super().delete()


class UserManager(BaseUserManager):
    def get_queryset(self):
        return CustomUserQuerySet(self.model, using=self._db)

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


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    @property
    def username(self):
        return f"{self.first_name} {self.last_name}".title()

    def __str__(self):
        return self.email

    def soft_delete(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def hard_delete(self):
        return super().delete()

    def delete(self, *args, **kwargs):
        raise RuntimeError("Gunakan soft_delete() atau hard_delete()")


class OTPVerifications(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    otp_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "used" if self.used_at else "unused"
        return f"{self.user.email} - {status} - {self.created_at}"

    @staticmethod
    def hash_otp(otp_code: str) -> str:
        return hashlib.sha256(otp_code.encode()).hexdigest()