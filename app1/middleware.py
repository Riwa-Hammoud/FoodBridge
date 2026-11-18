import logging

from django.shortcuts import redirect

from .permissions import get_role

AUTH_PAGES = {'/login-register/', '/login/', '/register/'}


class RedirectHomeMiddleware:
    """Send visitors to the right page. Views enforce access on their own."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if not request.user.is_authenticated:
            if path.startswith('/dashboard/'):
                return redirect('/login/')
            if path == '/logout/':
                return redirect('/')
        else:
            role = get_role(request.user)
            if role and (path == '/' or path in AUTH_PAGES):
                return redirect(f'/dashboard/{role}/')
        return self.get_response(request)


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger(__name__)

    def __call__(self, request):
        self.logger.info('Request: %s %s', request.method, request.path)
        response = self.get_response(request)
        self.logger.info('Response: %s %s', response.status_code, response.reason_phrase)
        return response