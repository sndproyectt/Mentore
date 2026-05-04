from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_teacherprofile_new_fields'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('apple', 'Apple')], max_length=20)),
                ('provider_id', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True)),
                ('avatar_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='social_accounts', to='auth.user')),
            ],
            options={'unique_together': {('provider', 'provider_id')}},
        ),
    ]
