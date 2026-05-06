from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_teacherprofile_theme_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='role',
            field=models.CharField(
                choices=[('coordinator', 'Coordinador'), ('teacher', 'Profesor')],
                default='teacher',
                max_length=20,
                verbose_name='Rol en el sistema',
            ),
        ),
    ]
