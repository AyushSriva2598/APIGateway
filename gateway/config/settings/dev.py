from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'dev-only-not-secret'
CSRF_TRUSTED_ORIGINS = ['http://localhost:8080']


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {'()': 'observability.formatters.JSONFormatter'},
    },
    'handlers': {
        'json': {'class': 'logging.StreamHandler', 'formatter': 'json'},
    },
    'root': {'level': 'DEBUG', 'handlers': ['json']},
}