import threading
from django.shortcuts import redirect

_thread_locals = threading.local()

def get_current_user():
    return getattr(_thread_locals, 'user', None)

class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, 'user', None)
        try:
            response = self.get_response(request)
        finally:
            if hasattr(_thread_locals, 'user'):
                del _thread_locals.user
        return response

class RoleSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            # Allowed login/logout endpoints
            allowed_paths = ['/admin/login/', '/admin/logout/', '/admin/jsi18n/']
            if request.path not in allowed_paths:
                if request.user.is_authenticated and not request.user.is_superuser:
                    if request.user.groups.filter(name='Teacher').exists():
                        return redirect('teacher_dashboard')
                    else:
                        return redirect('dashboard')
        return self.get_response(request)
