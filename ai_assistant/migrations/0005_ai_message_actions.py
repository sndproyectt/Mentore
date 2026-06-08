# Generated manually for AI message actions.

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def create_initial_versions(apps, schema_editor):
    ChatHistory = apps.get_model('ai_assistant', 'ChatHistory')
    AIMessageVersion = apps.get_model('ai_assistant', 'AIMessageVersion')
    versions = []
    now = timezone.now()
    for chat in ChatHistory.objects.all().only('id', 'ai_response'):
        if chat.ai_response:
            versions.append(AIMessageVersion(
                message_id=chat.id,
                content=chat.ai_response,
                numero_version=1,
                created_at=now,
            ))
    AIMessageVersion.objects.bulk_create(versions, ignore_conflicts=True, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0004_generateddocument'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='chathistory',
            name='document_context',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.CreateModel(
            name='AIMessageVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('numero_version', models.PositiveIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='ai_assistant.chathistory')),
            ],
            options={
                'verbose_name': 'Version de respuesta IA',
                'verbose_name_plural': 'Versiones de respuestas IA',
                'ordering': ['numero_version'],
                'unique_together': {('message', 'numero_version')},
            },
        ),
        migrations.CreateModel(
            name='AIFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.SmallIntegerField(choices=[(1, 'Positivo'), (-1, 'Negativo')])),
                ('fecha', models.DateTimeField(auto_now=True)),
                ('mensaje', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='ai_assistant.chathistory')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_feedback', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Feedback de IA',
                'verbose_name_plural': 'Feedback de IA',
                'unique_together': {('usuario', 'mensaje')},
            },
        ),
        migrations.CreateModel(
            name='AIDownloadLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('formato', models.CharField(max_length=10)),
                ('filename', models.CharField(max_length=255)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('mensaje', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='download_logs', to='ai_assistant.chathistory')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_download_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Descarga de respuesta IA',
                'verbose_name_plural': 'Descargas de respuestas IA',
                'ordering': ['-fecha'],
            },
        ),
        migrations.AddIndex(
            model_name='aifeedback',
            index=models.Index(fields=['mensaje', 'tipo'], name='ai_assistan_mensaje_977d8b_idx'),
        ),
        migrations.AddIndex(
            model_name='aifeedback',
            index=models.Index(fields=['usuario', 'fecha'], name='ai_assistan_usuario_d1aa56_idx'),
        ),
        migrations.AddIndex(
            model_name='aidownloadlog',
            index=models.Index(fields=['usuario', 'fecha'], name='ai_assistan_usuario_3b14bd_idx'),
        ),
        migrations.AddIndex(
            model_name='aidownloadlog',
            index=models.Index(fields=['mensaje', 'formato'], name='ai_assistan_mensaje_25c923_idx'),
        ),
        migrations.RunPython(create_initial_versions, migrations.RunPython.noop),
    ]
