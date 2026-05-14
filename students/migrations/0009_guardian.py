from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0008_reply_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Guardian',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Nombre')),
                ('email', models.EmailField(blank=True, verbose_name='Correo')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Teléfono')),
                ('relationship', models.CharField(blank=True, max_length=60, verbose_name='Parentesco')),
                ('is_primary', models.BooleanField(default=False, verbose_name='Principal')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='guardians',
                    to='students.student',
                )),
            ],
            options={
                'verbose_name': 'Acudiente',
                'verbose_name_plural': 'Acudientes',
                'ordering': ['-is_primary', 'name'],
            },
        ),
    ]