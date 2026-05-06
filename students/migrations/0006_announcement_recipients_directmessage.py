from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_classroom_teachers_m2m'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # M2M: docentes destinatarios del comunicado
        migrations.AddField(
            model_name='announcement',
            name='teacher_recipients',
            field=models.ManyToManyField(
                blank=True,
                related_name='received_announcements',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Docentes destinatarios',
            ),
        ),
        # M2M: estudiantes destinatarios (para padres)
        migrations.AddField(
            model_name='announcement',
            name='student_recipients',
            field=models.ManyToManyField(
                blank=True,
                related_name='received_announcements',
                to='students.student',
                verbose_name='Estudiantes (para notif. a padres)',
            ),
        ),
        # Nuevo modelo DirectMessage (docente → docente)
        migrations.CreateModel(
            name='DirectMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('subject', models.CharField(max_length=200, verbose_name='Asunto')),
                ('body', models.TextField(verbose_name='Mensaje')),
                ('is_read', models.BooleanField(default=False)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='sent_direct_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_direct_messages',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-sent_at'], 'verbose_name': 'Mensaje interno', 'verbose_name_plural': 'Mensajes internos'},
        ),
    ]
