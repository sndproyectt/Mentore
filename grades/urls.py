from django.urls import path
from . import views

app_name = 'grades'

urlpatterns = [
    path('', views.grade_list, name='list'),
    path('new/', views.grade_create, name='create'),
    path('<int:pk>/edit/', views.grade_edit, name='edit'),
    path('<int:pk>/delete/', views.grade_delete, name='delete'),
]
