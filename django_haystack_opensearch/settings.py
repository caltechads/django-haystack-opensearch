from typing import Any, Dict, List  # noqa: UP035

from django.conf import settings
from django.templatetags.static import static

app_settings: Dict[str, Any] = getattr(
    settings, f"DJANGO_HAYSTACK_OPENSEARCH_SETTINGS", {}
)
