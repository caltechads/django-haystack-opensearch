"""
Wildewidgets for the core app.

We're putting the navigation menus and breadcrumbs here so that we can share
them between the ops and users apps without circular imports.
"""

from typing import Any, ClassVar

from django.templatetags.static import static
from django.urls import reverse_lazy
from wildewidgets import (
    Block,
    BreadcrumbBlock,
    LinkedImage,
    Menu,
    MenuItem,
    TablerVerticalNavbar,
)


class MainMenu(Menu):
    """
    The primary navigation menu for the Administration interface.

    Example:
        >>> menu = MainMenu()
        >>> menu.activate("Buildings")
        >>> menu.build_menu(menu.items)

    """

    #: Default menu items that appear for all users
    items: ClassVar[list[MenuItem]] = [
        MenuItem(
            text="Home",
            icon="house",
            url=reverse_lazy("core:home"),
        ),
    ]


class NavigationSidebar(TablerVerticalNavbar):
    """
    The vertical navigation sidebar for the Operations app.

    This sidebar displays on the left side of the page and contains the main
    navigation menu for the ops and users apps. It includes Caltech branding and
    can be hidden on smaller viewports for responsive design.

    The sidebar uses the :class:`~wildewidgets.TablerVerticalNavbar` base class
    which provides the responsive behavior and styling. It automatically hides
    below the ``xl`` viewport breakpoint to save space on smaller screens.

    Data Sources:
        - Branding image comes from Django's static file system
        - Menu contents come from :class:`MainMenu` instance
    """

    #: The breakpoint at which the sidebar should be hidden for responsive design
    hide_below_viewport: str = "xl"

    #: The branding block that appears at the top of the sidebar
    branding = Block(
        LinkedImage(
            image_src=static("core/images/logo.jpg"),
            image_width="150px",
            image_alt="django_haystack_opensearch",
            css_class="d-flex justify-content-center ms-3",
            url="https://localhost/",
        ),
    )

    #: The content of the sidebar -- our main navigation menu
    contents: ClassVar[list[Block]] = [
        MainMenu(),
    ]


class Breadcrumbs(BreadcrumbBlock):
    """
    Base breadcrumb navigation for ops app pages.

    This class provides a consistent breadcrumb trail that starts with the
    ops home page for all pages in the ops app. It ensures
    users always know where they are in page hierarchy.

    The breadcrumbs use a consistent styling with white text and provide
    navigation back to the main ops area.

    Example:
        >>> breadcrumbs = Breadcrumbs()
        >>> # Automatically includes "Caltech Building Directory Admin" as the first
        >>> # breadcrumb with a link to the ops home page

    """

    #: CSS class to apply to breadcrumb titles for consistent styling
    title_class: ClassVar[str] = "text-white"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the breadcrumbs with the django_haystack_opensearch home link.

        This method automatically adds the first breadcrumb item pointing to the
        django_haystack_opensearch home page, ensuring all breadcrumb trails
        start from the same root location.

        Args:
            *args: Variable length argument list passed to parent BreadcrumbBlock

        Keyword Args:
            **kwargs: Arbitrary keyword arguments passed to parent BreadcrumbBlock

        """
        super().__init__(*args, **kwargs)
        self.add_breadcrumb(
            "django_haystack_opensearch Demo", reverse_lazy("core:home")
        )
