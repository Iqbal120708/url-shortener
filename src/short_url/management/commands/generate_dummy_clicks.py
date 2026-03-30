from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from short_url.models import ShortUrl, Click
from short_url.utils import generate_short_code, extract_domain

from user_agents import parse

User = get_user_model()

import requests
import random

FAKE_IPS = [
    ["103.10.20.30", "ID"],
    ["8.8.8.8", "US"],
    ["31.13.64.1", "IE"],
    ["49.50.60.70", "KR"],
    ["202.80.90.100", "ID"],
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
]

REFERERS = [
    "https://google.com/search?q=example",
    "https://twitter.com/home",
    "https://facebook.com/feed",
    "",
    "https://instagram.com",
]

def generate_dummy_click(i, short_url):
    ip = random.choice(FAKE_IPS)
    ua = random.choice(USER_AGENTS)
    referer = random.choice(REFERERS)

    browser = None
    os = None
    device_type = None
    country = None

    if ua:
        ua = parse(ua)

        # user_agent = ua_string
        browser = ua.browser.family
        os = ua.os.family
        device_type = (
            "Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "Desktop"
        )

    return Click(
        short_url=short_url,
        ip_address=ip[0],
        user_agent=ua,
        referer=referer,
        referer_domain=extract_domain(referer),
        browser=browser,
        os=os,
        device_type=device_type,
        country_code=ip[1],
    )
    
class Command(BaseCommand):
    help = "Generate 100 rows clicks data"

    def handle(self, *args, **options):
        user = User.objects.create_user(
            username="test dummy data",
            email="dummydata@gmail.com",
            password="secret1234",
        )

        short_url = ShortUrl.objects.create(
            short_code=generate_short_code(),
            original_url="http://localhost:5000/api/v1/organizations/1/departments/3/employees/7/projects/42/tasks/108/comments",
            user=user,
        )
        
        clicks = []
        for i in range(100):
            click = generate_dummy_click(i, short_url)
            clicks.append(click)
        
        Click.objects.bulk_create(clicks)
        self.stdout.write("Successfully generate 100 rows data")
