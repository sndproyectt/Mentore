from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from students.views import parent_portal, parent_portal_auto

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/dashboard/'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('students.urls')),
    path('grades/', include('grades.urls')),
    path('ai/', include('ai_assistant.urls')),
    path('gallery/', include('gallery.urls')),
    path('dashboard/calendar/', include('calendar_app.urls')),
    # Panel de coordinación
    path('coordinacion/', include('coordinator.urls')),
    # Portal público para padres
    path('padres/', parent_portal, name='parent_portal'),
    path('padres/auto/', parent_portal_auto, name='parent_portal_auto'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
