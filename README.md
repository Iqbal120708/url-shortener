# Url Shortener

A URL shortener REST API with click analytics, built with Django, DRF, PostgreSQL, Celery, and Redis.

# Tech and Version

- Python 3.13
- PostgreSQL 18.2
- Redis 8.6.1

# Framework and Liblary

- Django 6.0
- Django Rest Framework 3.16
- Celery 5.6

# Features

- Authentication and authorization with jwt
- Manage short urls - list (`is_active` query param), get detail, create, and delete
- implementation soft delete for short url
- Redirect short url to original url

# Environment variables

- `DEBUG=True`
- `SECRET_KEY=your-secret-key`
- `DB_NAME=postgres`
- `DB_USER=user`
- `DB_PASSWORD=password`
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `ALLOWED_HOSTS=localhost`
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_HOST_USER=youremail@gmail.com`
- `EMAIL_HOST_PASSWORD=abcdefghijklmnop`
- `REDIS_URL=redis://localhost:6379/0`

# Performance

- **Database indexing** – `short_code` and `ip_address` fields indexed for redirect lookup
- **Redis caching** – Redirect targets cached with 24-hour to reduce DB hits
- **Async task click analytics** – Celery click tasks are executed asynchronously

# How to run

- clone the repo
```
git clone https://github.com/Iqbal120708/url-shortener
cd url-shortener
```

- Run python environment
```
python -m venv env
source env/bin/activate
```

- install dependencies
```
pip install -r requirements.txt
```

- Create a `.env` file and set the required variables.

- Run database migrations
```
cd src
python manage.py migrate
```

- Run the redis server
```
redis-server
```

- Run the postgres server

- Run the server
```
cd src
python manage.py runserver
```
