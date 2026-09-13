from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class APIKeyAuthentication(BaseAuthentication):
    """DRF-level authentication class. Relies on APIKeyAuthMiddleware having
    already validated the header and attached request.api_key — this class
    just tells DRF's views/permissions that the request is authenticated."""

    def authenticate(self, request):
        api_key = getattr(request, 'api_key', None)

        if not api_key:
            return None  # let DRF fall through to "unauthenticated"

        # No real user model tied to API keys yet (Day 2/4) — (None, api_key)
        # tells DRF "authenticated, but no Django User object attached"
        return (None, api_key)