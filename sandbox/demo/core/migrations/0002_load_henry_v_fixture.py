# Generated migration to load henry_v fixture

from django.db import migrations
from django.core.management import call_command

fixture = "henry_v"


def load_fixture(apps, schema_editor):
    call_command("loaddata", fixture, app_label="core")


def unload_fixture(apps, schema_editor):
    Play = apps.get_model("core", "Play")
    Play.objects.filter(title="Henry V").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_fixture, reverse_code=unload_fixture),
    ]
