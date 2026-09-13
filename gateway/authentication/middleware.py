class APIKeyAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ('/healthz', '/metrics') or request.path.startswith('/admin'):
            return self.get_response(request)

        api_key = request.headers.get('X-API-Key')

        if not api_key:
            from django.http import JsonResponse
            return JsonResponse({'detail': 'X-API-Key header required'}, status=401)

        request.api_key = api_key
        return self.get_response(request)