from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_teacherprofile_avatar_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='theme_color',
            field=models.CharField(blank=True, default='ocean', max_length=30, verbose_name='Tema de color'),
        ),
    ]
