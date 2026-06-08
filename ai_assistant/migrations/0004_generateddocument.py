# Generated manually for AI generated documents.

import ai_assistant.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0003_chatdocument'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneratedDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=ai_assistant.models.ai_generated_document_path)),
                ('original_name', models.CharField(max_length=255)),
                ('file_format', models.CharField(choices=[('pdf', 'PDF'), ('docx', 'Word'), ('xlsx', 'Excel'), ('csv', 'CSV'), ('txt', 'Texto'), ('md', 'Markdown')], max_length=10)),
                ('file_size', models.PositiveIntegerField(default=0)),
                ('source_prompt', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_generated_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Documento generado por IA',
                'verbose_name_plural': 'Documentos generados por IA',
                'ordering': ['-created_at'],
            },
        ),
    ]
