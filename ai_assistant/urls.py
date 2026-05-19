from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send'),
    path('stream/', views.stream_message, name='stream'),
    path('clear/', views.clear_history, name='clear'),
    path('documents/', views.list_documents, name='documents'),
    path('documents/upload/', views.upload_document, name='document_upload'),
    path('documents/<int:pk>/delete/', views.delete_document, name='document_delete'),
]
