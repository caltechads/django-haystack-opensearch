from typing import ClassVar

from braces.views import LoginRequiredMixin
from django.views.generic import View
from wildewidgets import (
    Block,
    BreadcrumbBlock,
    Navbar,
    NavbarMixin,
    StandardWidgetMixin,
)

from .wildewidgets import Breadcrumbs, NavigationSidebar


class DemoStandardMixin(LoginRequiredMixin, StandardWidgetMixin, NavbarMixin):
    template_name: ClassVar[str] = "demo/intermediate.html"
    navbar_class: ClassVar[Navbar] = NavigationSidebar


class HomeView(DemoStandardMixin, View):
    def get_content(self) -> Block:
        return Block(
            "Hello from django_haystack_opensearch Demo",
            tag="h2",
        )

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        return Breadcrumbs()
