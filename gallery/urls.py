from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.gallery_list, name='list'),
    path('upload/', views.work_upload, name='upload'),
    path('<int:pk>/', views.work_detail, name='detail'),
    path('<int:pk>/delete/', views.work_delete, name='delete'),
    path('parents/', views.parent_gallery, name='parent_gallery'),
]
