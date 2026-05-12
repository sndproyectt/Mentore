from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grades', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='grade',
            name='subject',
            field=models.CharField(
                blank=True, default='',
                help_text='Materia a la que pertenece esta nota',
                max_length=100,
                verbose_name='Materia',
            ),
            preserve_default=False,
        ),
    ]
