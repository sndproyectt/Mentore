from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0002_grade_subject'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Crear modelo Subject
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120, unique=True, verbose_name='Nombre')),
                ('code', models.CharField(blank=True, max_length=20, verbose_name='Código')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('active', models.BooleanField(default=True, verbose_name='Activa')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Materia', 'verbose_name_plural': 'Materias'},
        ),
        # 2. Crear modelo TeacherSubject
        migrations.CreateModel(
            name='TeacherSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('teacher', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='teacher_subjects',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Docente',
                )),
                ('subject', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='teacher_assignments',
                    to='grades.subject',
                    verbose_name='Materia',
                )),
            ],
            options={
                'unique_together': {('teacher', 'subject')},
                'ordering': ['subject__name'],
                'verbose_name': 'Materia asignada',
                'verbose_name_plural': 'Materias asignadas',
            },
        ),
        # 3. Renombrar campo subject (CharField) → subject_text en Grade
        migrations.RenameField(
            model_name='grade',
            old_name='subject',
            new_name='subject_text',
        ),
        migrations.AlterField(
            model_name='grade',
            name='subject_text',
            field=models.CharField(
                blank=True, max_length=100,
                verbose_name='Materia (texto)',
                help_text='Solo para datos migrados. Usa el campo Materia (FK).',
            ),
        ),
        # 4. Agregar FK subject → Subject en Grade
        migrations.AddField(
            model_name='grade',
            name='subject',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='grades',
                to='grades.subject',
                verbose_name='Materia',
            ),
        ),
    ]
