# Generated migration to add fields to Play and Speech models
# This must run BEFORE the fixture is loaded

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='play',
            name='created',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='speech',
            name='created_date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='speech',
            name='is_soliloquy',
            field=models.BooleanField(default=False),
        ),
    ]






