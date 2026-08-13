from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from short_url.models import ShortUrl
from short_url.utils import generate_short_code

User = get_user_model()


class Command(BaseCommand):
    help = "Generate 1 000 000 rows short url"

    def handle(self, *args, **options):
        try:
            user = User.objects.create_user(
                first_name="first",
                last_name="last",
                email="dummydata@gmail.com",
                password="secret1234",
            )
        except IntegrityError:
            user = User.objects.get(email="dummydata@gmail.com")

        data = [
            ShortUrl(
                short_code=generate_short_code(),
                original_url="https://dev.to/iqbal120708/preventing-overselling-with-stock-reservation-and-selectforupdate-in-django-3jam",
                user=user,
            )
            for _ in range(200)
        ]
        ShortUrl.objects.bulk_create(data, batch_size=10000)

        self.stdout.write("Successfully generte 200 rows data")
