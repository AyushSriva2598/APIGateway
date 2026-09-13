from django.http import JsonResponse
from django.views import View
from django.db import connection
import redis
from django.conf import settings


class HealthCheckView(View):
    def get(self, request):
        checks = {'database': self._check_db(), 'redis': self._check_redis()}
        healthy = all(checks.values())
        return JsonResponse(
            {'status': 'ok' if healthy else 'degraded', 'checks': checks},
            status=200 if healthy else 503,
        )

    def _check_db(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return True
        except Exception:
            return False

    def _check_redis(self):
        try:
            r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
            return r.ping()
        except Exception:
            return False