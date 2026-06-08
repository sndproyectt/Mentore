from django.urls import path
from . import views

app_name = 'ai_assistant'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send'),
    path('stream/', views.stream_message, name='stream'),
    path('clear/', views.clear_history, name='clear'),
    path('preferences/global/', views.global_assistant_preferences, name='global_preferences'),
    path('documents/', views.list_documents, name='documents'),
    path('documents/upload/', views.upload_document, name='document_upload'),
    path('documents/<int:pk>/delete/', views.delete_document, name='document_delete'),
    path('generated-documents/<int:pk>/download/', views.download_generated_document, name='generated_document_download'),
    path('messages/<int:pk>/copy/', views.message_copy_payload, name='message_copy'),
    path('messages/<int:pk>/feedback/', views.message_feedback, name='message_feedback'),
    path('messages/<int:pk>/download/', views.download_message_response, name='message_download'),
    path('messages/<int:pk>/regenerate/', views.regenerate_message, name='message_regenerate'),
    path('messages/<int:pk>/tts/', views.message_tts, name='message_tts'),
    path('generate-image/', views.generate_image, name='generate_image'),
]
