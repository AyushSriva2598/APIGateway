import requests
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework.views import APIView

from .router import resolve_backend

# Headers that are connection-specific and must not be forwarded as-is
HOP_BY_HOP_HEADERS = {
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'transfer-encoding', 'upgrade', 'host',
}


class ProxyView(APIView):
    """Forwards any request DRF's auth/rate-limit middleware already allowed
    through to the resolved backend, streaming the response back untouched."""

    def dispatch(self, request, *args, **kwargs):
        # bypass DRF's content negotiation/renderer machinery entirely —
        # we're passing bytes through, not rendering DRF Response objects
        return self._proxy(request)

    def _proxy(self, request):
        path = '/' + request.path.lstrip('/')
        upstream = resolve_backend(path)

        if upstream is None:
            return JsonResponse({'detail': 'no route for this path'}, status=404)

        upstream_url = upstream.rstrip('/') + path

        forward_headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in HOP_BY_HOP_HEADERS
        }

        try:
            upstream_response = requests.request(
                method=request.method,
                url=upstream_url,
                headers=forward_headers,
                data=request.body,
                params=request.GET,
                stream=True,
                timeout=10,
            )
        except requests.exceptions.ConnectionError:
            return JsonResponse({'detail': 'upstream unavailable'}, status=502)
        except requests.exceptions.Timeout:
            return JsonResponse({'detail': 'upstream timed out'}, status=504)

        response = StreamingHttpResponse(
            streaming_content=upstream_response.iter_content(chunk_size=8192),
            status=upstream_response.status_code,
            content_type=upstream_response.headers.get('Content-Type', 'application/octet-stream'),
        )

        for header, value in upstream_response.headers.items():
            if header.lower() not in HOP_BY_HOP_HEADERS | {'content-type', 'content-length'}:
                response[header] = value

        return response