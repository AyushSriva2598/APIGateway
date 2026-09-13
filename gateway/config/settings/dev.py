from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY = 'dev-only-not-secret'

# REDIS_HOST/PORT and DATABASES already resolve to 'redis' / 'postgres'
# via base.py env defaults — those match the docker-compose service names,
# so nothing to override here.

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'level': 'DEBUG', 'handlers': ['console']},
}