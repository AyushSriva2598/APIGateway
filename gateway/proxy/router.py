from django.conf import settings


def resolve_backend(path: str) -> str | None:
    """Return the upstream base URL for a request path, or None if no route matches."""
    for prefix, upstream in settings.BACKEND_ROUTES.items():
        if path.startswith(prefix):
            return upstream
    return None