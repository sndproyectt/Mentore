from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='is_homeroom_teacher',
            field=models.BooleanField(default=False, verbose_name='¿Es director(a) de grupo?'),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='homeroom_group',
            field=models.CharField(blank=True, max_length=100, verbose_name='Grupo a cargo (dirección)'),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='school_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='Nombre del colegio'),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='city',
            field=models.CharField(blank=True, max_length=100, verbose_name='Ciudad'),
        ),
    ]
