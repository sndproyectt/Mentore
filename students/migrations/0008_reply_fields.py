from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0007_alter_classroom_teacher_alter_directmessage_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='directmessage',
            name='reply_to',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='replies',
                to='students.directmessage',
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='reply_to',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='replies',
                to='students.message',
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='sender_label',
            field=models.CharField(
                blank=True, default='',
                max_length=60,
                verbose_name='Enviado por',
            ),
        ),
    ]