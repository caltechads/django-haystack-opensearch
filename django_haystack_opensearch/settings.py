from typing import Any

from django.conf import settings

app_settings: dict[str, Any] = getattr(
    settings, "DJANGO_HAYSTACK_OPENSEARCH_SETTINGS", {}
)
