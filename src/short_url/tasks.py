import httpx
from celery import shared_task
from user_agents import parse

from .models import Click, ShortUrl
from .utils import extract_domain


def get_country(ip_address):
    try:
        response = httpx.get(f"http://ip-api.com/json/{ip_address}", timeout=3.0)
        return response.json().get("countryCode")
    except Exception:
        return None


@shared_task
def track_click(short_url_id, ip_address, referer, user_agent):
    short_url = ShortUrl.objects.filter(id=short_url_id).first()
    if not short_url:
        return

    browser = None
    os = None
    device_type = None
    country = None

    if user_agent:
        ua = parse(user_agent)

        # user_agent = ua_string
        browser = ua.browser.family
        os = ua.os.family
        device_type = (
            "Mobile" if ua.is_mobile else "Tablet" if ua.is_tablet else "Desktop"
        )

    if ip_address:
        country_code = get_country(ip_address)

    Click.objects.create(
        short_url=short_url,
        ip_address=ip_address,
        user_agent=user_agent,
        referer=referer,
        referer_domain=extract_domain(referer),
        browser=browser,
        os=os,
        device_type=device_type,
        country_code=country_code,
    )
