from django.urls import path
from . import views

app_name = "calendar_app"

urlpatterns = [
    path("", views.schedule_view, name="schedule"),
    path("oauth/start/", views.oauth_start, name="oauth_start"),
    path("oauth/callback/", views.oauth_callback, name="oauth_callback"),
    path("oauth/disconnect/", views.oauth_disconnect, name="oauth_disconnect"),
    path("api/events/", views.api_events, name="api_events"),
    path("api/events/<str:event_id>/", views.api_event_detail, name="api_event_detail"),
]
