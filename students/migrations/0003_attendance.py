from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_announcement'),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Fecha')),
                ('status', models.CharField(choices=[('present', 'Presente'), ('absent', 'Ausente'), ('late', 'Tarde'), ('excused', 'Excusa')], default='present', max_length=10)),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='Nota')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='students.student')),
            ],
            options={'verbose_name': 'Asistencia', 'verbose_name_plural': 'Asistencias', 'ordering': ['-date'], 'unique_together': {('student', 'date')}},
        ),
    ]
