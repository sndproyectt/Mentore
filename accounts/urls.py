from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/',                    views.login_view,      name='login'),
    path('register/',                 views.register_view,   name='register'),
    path('logout/',                   views.logout_view,     name='logout'),
    path('profile/',                  views.profile_view,    name='profile'),
    # Social login
    path('social/google/',            views.google_login,    name='google_login'),
    path('social/google/callback/',   views.google_callback, name='google_callback'),
    path('social/apple/',             views.apple_login,     name='apple_login'),
    path('social/apple/callback/',    views.apple_callback,  name='apple_callback'),
]
