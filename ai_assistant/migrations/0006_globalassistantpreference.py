from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_assistant', '0005_ai_message_actions'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GlobalAssistantPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('avatar', models.CharField(choices=[('avatar_a', 'Avatar normal'), ('avatar_b', 'Avatar transparente')], default='avatar_a', max_length=40)),
                ('size', models.CharField(choices=[('small', 'Pequeno'), ('medium', 'Mediano'), ('large', 'Grande'), ('xlarge', 'Extra grande')], default='medium', max_length=20)),
                ('position', models.CharField(choices=[('bottom_right', 'Inferior derecha'), ('bottom_left', 'Inferior izquierda')], default='bottom_right', max_length=20)),
                ('transparency', models.PositiveSmallIntegerField(default=0)),
                ('border_color', models.CharField(choices=[('mentore_blue', 'Azul Mentore'), ('green', 'Verde'), ('purple', 'Morado'), ('gray', 'Gris'), ('black', 'Negro'), ('none', 'Sin borde')], default='mentore_blue', max_length=20)),
                ('shadow', models.CharField(choices=[('none', 'Sin sombra'), ('soft', 'Sombra suave'), ('medium', 'Sombra media'), ('intense', 'Sombra intensa')], default='medium', max_length=20)),
                ('animations_enabled', models.BooleanField(default=True)),
                ('activity_effect', models.CharField(choices=[('halo', 'Halo luminoso'), ('glow', 'Brillo pulsante'), ('pulse', 'Pulso'), ('none', 'Ninguno')], default='halo', max_length=20)),
                ('is_visible', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='global_assistant_preference', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Preferencia del asistente global',
                'verbose_name_plural': 'Preferencias del asistente global',
            },
        ),
    ]
