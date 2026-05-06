"""
Decoradores de control de acceso por rol para Mentore.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib import messages


def get_role(user):
    """Devuelve el rol del usuario o 'teacher' como fallback."""
    try:
        return user.teacher_profile.role
    except Exception:
        return 'teacher'


def coordinator_required(view_func):
    """Solo permite acceso a usuarios con rol coordinador."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if get_role(request.user) != 'coordinator':
            messages.error(request, 'Acceso restringido: solo para coordinadores.')
            return redirect('students:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_or_coordinator_required(view_func):
    """Permite acceso a profesores y coordinadores."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        role = get_role(request.user)
        if role not in ('teacher', 'coordinator'):
            messages.error(request, 'Acceso restringido.')
            return redirect('students:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
