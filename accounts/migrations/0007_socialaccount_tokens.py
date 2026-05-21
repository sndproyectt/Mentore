from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_teacherprofile_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='socialaccount',
            name='access_token',
            field=models.TextField(blank=True, default='', verbose_name='Access Token'),
        ),
        migrations.AddField(
            model_name='socialaccount',
            name='refresh_token',
            field=models.TextField(blank=True, default='', verbose_name='Refresh Token'),
        ),
        migrations.AddField(
            model_name='socialaccount',
            name='token_expiry',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Token Expiry'),
        ),
    ]