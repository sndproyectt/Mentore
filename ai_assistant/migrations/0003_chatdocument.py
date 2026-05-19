# Generated manually for ChatDocument

import ai_assistant.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ai_assistant', '0002_alter_chathistory_options_conversationsummary_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=ai_assistant.models.ai_document_upload_path)),
                ('original_name', models.CharField(max_length=255)),
                ('file_type', models.CharField(blank=True, max_length=20)),
                ('file_size', models.PositiveIntegerField(default=0)),
                ('extracted_text', models.TextField(blank=True)),
                ('extraction_error', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Documento del chat',
                'verbose_name_plural': 'Documentos del chat',
                'ordering': ['-created_at'],
            },
        ),
    ]
