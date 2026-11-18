from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

ROLE_RESTAURANT = 'R'
ROLE_NGO = 'N'


def get_role(user):
    """Return 'R', 'N' or None. The Restaurant/NGO profile is the source of truth."""
    if not user.is_authenticated:
        return None
    if hasattr(user, 'restaurant'):
        return ROLE_RESTAURANT
    if hasattr(user, 'ngo'):
        return ROLE_NGO
    return None


def get_profile(user):
    role = get_role(user)
    if role == ROLE_RESTAURANT:
        return user.restaurant
    if role == ROLE_NGO:
        return user.ngo
    return None


def role_required(role):
    """Anonymous -> login page. Logged in with the wrong role -> 403."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if get_role(request.user) != role:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


restaurant_required = role_required(ROLE_RESTAURANT)
ngo_required = role_required(ROLE_NGO)