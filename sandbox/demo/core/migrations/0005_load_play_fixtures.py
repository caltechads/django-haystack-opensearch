# Generated migration to load henry_v fixture
# This must run AFTER the fields are added

from django.core.management import call_command
from django.db import migrations

fixtures = ["henry_v", "macbeth"]


def load_fixture(apps, schema_editor):
    for fixture in fixtures:
        call_command("loaddata", fixture, app_label="core")


def unload_fixture(apps, schema_editor):
    Play = apps.get_model("core", "Play")
    Play.objects.filter(title="Henry V").delete()
    Play.objects.filter(title="Macbeth").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_alter_scene_unique_together_scene_play_and_more"),
    ]

    operations = [
        migrations.RunPython(load_fixture, reverse_code=unload_fixture),
    ]
