from django.conf import settings
from django.http import HttpRequest


def add_version(request: HttpRequest) -> dict[str, str]:  # noqa: ARG001
    """
    Add the version of the application to the context.

    Args:
        request: the request object

    Returns:
        A dictionary with one key, "VERSION", whose value is the version of the
        application.

    """
    return {
        "VERSION": settings.VERSION,
    }
