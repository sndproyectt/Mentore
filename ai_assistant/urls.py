from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send'),
    path('clear/', views.clear_history, name='clear'),
]
