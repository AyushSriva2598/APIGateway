from .base import *
import os

DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']          # fail loud if missing
ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')

# SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {'()': 'observability.formatters.JSONFormatter'},
    },
    'handlers': {
        'json': {'class': 'logging.StreamHandler', 'formatter': 'json'},
    },
    'root': {'level': 'INFO', 'handlers': ['json']},
}