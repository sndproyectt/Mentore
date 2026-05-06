from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_message'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='classroom',
            name='teachers',
            field=models.ManyToManyField(
                blank=True,
                related_name='shared_classrooms',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Docentes con acceso',
            ),
        ),
    ]
