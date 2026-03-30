import secrets
import string

ALPHABET = string.ascii_letters + string.digits


def generate_short_code(length=7):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


from urllib.parse import urlparse


def extract_domain(url):
    if not url:
        return "direct"
    parsed = urlparse(url)
    return parsed.netloc or "direct"
