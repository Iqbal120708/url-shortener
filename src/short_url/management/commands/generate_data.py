from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from short_url.models import ShortUrl
from short_url.utils import generate_short_code

User = get_user_model()


class Command(BaseCommand):
    help = "Generate 1 000 000 rows short url"

    def handle(self, *args, **options):
        user = User.objects.create_user(
            username="test dummy data",
            email="dummydata@gmail.com",
            password="secret1234",
        )

        data = [
            ShortUrl(
                short_code=generate_short_code(),
                original_url="http://localhost:5000/api/v1/organizations/1/departments/3/employees/7/projects/42/tasks/108/comments",
                user=user,
            )
            for _ in range(1_000_000)
        ]
        ShortUrl.objects.bulk_create(data, batch_size=10000)

        self.stdout.write("Successfully generte 1 000 000 rows data")
