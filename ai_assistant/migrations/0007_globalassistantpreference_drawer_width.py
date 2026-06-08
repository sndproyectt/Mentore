from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0006_globalassistantpreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='globalassistantpreference',
            name='drawer_width',
            field=models.PositiveSmallIntegerField(default=520),
        ),
    ]
