from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Título')),
                ('content', models.TextField(verbose_name='Contenido')),
                ('priority', models.CharField(choices=[('low', 'Informativo'), ('medium', 'Importante'), ('high', 'Urgente')], default='low', max_length=10, verbose_name='Prioridad')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('classroom', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='announcements', to='students.classroom', verbose_name='Grupo')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Comunicado', 'verbose_name_plural': 'Comunicados', 'ordering': ['-created_at']},
        ),
    ]
