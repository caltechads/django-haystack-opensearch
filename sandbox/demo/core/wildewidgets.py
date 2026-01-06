"""
Wildewidgets for the core app.

We're putting the navigation menus and breadcrumbs here so that we can share
them between the ops and users apps without circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags
from wildewidgets import (
    BasicModelTable,
    Block,
    BreadcrumbBlock,
    CardWidget,
    Column,
    CrispyFormWidget,
    HorizontalLayoutBlock,
    LinkButton,
    LinkedImage,
    Menu,
    MenuItem,
    PagedModelWidget,
    Row,
    TablerVerticalNavbar,
    TagBlock,
    WidgetListLayoutHeader,
)

if TYPE_CHECKING:
    from django.db.models import Model, QuerySet
    from django.forms import Form
    from haystack.models import SearchResult
    from haystack.query import SearchQuerySet

from demo.core.forms import BasicSearchForm
from demo.core.models import Play, Speaker


class MainMenu(Menu):
    """
    The primary navigation menu for the demo application.

    Provides navigation to all demo views including search, filtering,
    facets, and index management functionality.

    Example:
        >>> menu = MainMenu()
        >>> menu.activate("Search")
        >>> menu.build_menu(menu.items)

    """

    #: Default menu items that appear for all users
    items: ClassVar[list[MenuItem]] = [
        MenuItem(
            text="Home",
            icon="house",
            url=reverse_lazy("core:home"),
        ),
        MenuItem(
            text="Admin",
            icon="shield-lock",
            url=reverse_lazy("admin:index"),
        ),
        MenuItem(
            text="Advanced Search",
            icon="sliders",
            url=reverse_lazy("core:advanced-search"),
        ),
        MenuItem(
            text="Filters",
            icon="funnel",
            url=reverse_lazy("core:filter-examples"),
        ),
        MenuItem(
            text="Facets",
            icon="tags",
            url=reverse_lazy("core:facets"),
        ),
        MenuItem(
            text="More Like This",
            icon="lightning",
            url=reverse_lazy("core:more-like-this"),
        ),
        MenuItem(
            text="Sorting",
            icon="sort-down",
            url=reverse_lazy("core:sorting"),
        ),
        MenuItem(
            text="Highlighting",
            icon="highlighter",
            url=reverse_lazy("core:highlighting"),
        ),
        MenuItem(
            text="Pagination",
            icon="collection",
            url=reverse_lazy("core:pagination"),
        ),
        MenuItem(
            text="Spelling",
            icon="spellcheck",
            url=reverse_lazy("core:spelling"),
        ),
        MenuItem(
            text="Field Selection",
            icon="list-check",
            url=reverse_lazy("core:field-selection"),
        ),
        MenuItem(
            text="Special Cases",
            icon="question-circle",
            url=reverse_lazy("core:special-cases"),
        ),
        MenuItem(
            text="Index Status",
            icon="database",
            url=reverse_lazy("core:index-status"),
        ),
        MenuItem(
            text="Index Management",
            icon="gear",
            url=reverse_lazy("core:index-management"),
        ),
    ]


class GlobalSearchFormWidget(CrispyFormWidget):
    """
    Encapsulates the :py:class:`sphinx_hosting.forms.GlobalSearchForm`.
    """

    name: str = "global-search"
    css_class: str = "mb-3"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.form is None:
            self.form = BasicSearchForm()


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
            image_src=static("core/images/logo.png"),
            image_width="220px",
            image_alt="django_haystack_opensearch",
            css_class="d-flex justify-content-center ms-1",
            url="https://localhost/",
        ),
        GlobalSearchFormWidget(css_class="ms-auto ms-xl-0 align-self-center mt-3"),
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


# -----------------------------------------------------------------------------
# Play Table Widgets
# -----------------------------------------------------------------------------


class PlayTable(BasicModelTable):
    """
    Data table for displaying plays.

    This table displays all plays in the database with their titles.
    It provides a simple view of available plays for the demo application.
    """

    #: The model to display in the table
    model: type[Model] = Play

    #: The number of rows to display per page
    page_length: int = 25

    #: Whether to use alternating row colors
    striped: bool = True

    #: The fields to display in the table
    fields: ClassVar[list[str]] = [
        "id",
        "title",
        "created",
    ]

    #: The verbose names for the fields
    verbose_names: ClassVar[dict[str, str]] = {
        "id": "ID",
        "title": "Title",
        "created": "Created",
    }

    def get_queryset(self) -> QuerySet:
        """
        Get the queryset of plays to display, ordered by title.

        Returns:
            QuerySet of all Play objects ordered by title.

        """
        return Play.objects.all().order_by("title")


class PlayTableWidget(CardWidget):
    """
    Widget for displaying a table of plays.

    This widget shows all plays in a card with a title header that includes
    a count badge. It provides a comprehensive view of all plays in the
    database.
    """

    #: The title displayed in the card header
    title: str = "Plays"

    #: The Bootstrap icon name to display in the card header
    icon: str = "book"

    #: The HTML name/ID for the widget for CSS styling and JavaScript
    name: str = "play-table"

    def __init__(self, **kwargs) -> None:
        """
        Initialize the PlayTableWidget.

        Keyword Args:
            **kwargs: Additional arguments passed to CardWidget.

        """
        super().__init__(widget=PlayTable(), **kwargs)

    def get_title(self) -> WidgetListLayoutHeader:
        """
        Build the header title with play count.

        Returns:
            A WidgetListLayoutHeader with the title and count badge.

        """
        count = Play.objects.count()
        return WidgetListLayoutHeader(
            header_text=self.title,
            badge_text=str(count),
        )


# -----------------------------------------------------------------------------
# Search Widgets
# -----------------------------------------------------------------------------


class SearchFormWidget(CrispyFormWidget):
    """
    Encapsulates the BasicSearchForm for the navigation sidebar.

    This widget provides a simple search form that can be used
    in the navigation area for quick searches.
    """

    name: str = "global-search"
    css_class: str = "mb-3"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.form is None:
            self.form = BasicSearchForm()


class SearchResultBlock(Block):
    """
    Block for rendering a single search result.

    This displays a search result with its text snippet, metadata,
    and score. Supports highlighting when available.

    Keyword Args:
        object: The SearchResult object to render.

    """

    block: str = "search-result"
    max_text_length: int = 300

    def __init__(self, object: SearchResult = None, **kwargs):  # noqa: A002
        result = object
        super().__init__(**kwargs)
        self.add_class("shadow")
        self.add_class("border")
        self.add_class("p-4")
        self.add_class("mb-4")

        if result is None:
            self.add_block(Block("No result provided", css_class="text-muted"))
            return

        # Header with model type and score
        model_name = result.model.__name__ if result.model else "Unknown"
        self.add_block(
            HorizontalLayoutBlock(
                Block(
                    model_name,
                    name="search-result__model",
                    css_class="badge bg-primary me-2",
                ),
                Block(
                    f"Score: {result.score:.2f}" if result.score else "",
                    name="search-result__score",
                    css_class="text-muted fs-6",
                ),
                justify="between",
                align="baseline",
                css_class="mb-2",
            )
        )

        # Title/main text
        title = self._get_title(result)
        self.add_block(Block(title, tag="h4", css_class="mb-2"))

        # Metadata
        metadata = self._get_metadata(result)
        if metadata:
            self.add_block(Block(metadata, css_class="text-muted fs-6 mb-2"))

        # Text snippet (use highlighted if available)
        text = self._get_text_snippet(result)
        if text:
            self.add_block(
                Block(text, name="search-result__snippet", css_class="fs-8 mb-3")
            )

    def _get_title(self, result: SearchResult) -> str:
        """Get the title for the search result."""
        if hasattr(result, "speaker_name") and result.speaker_name:
            return f"{result.speaker_name}"
        if hasattr(result, "title") and result.title:
            return result.title
        if hasattr(result, "name") and result.name:
            return result.name
        return str(result.pk)

    def _get_metadata(self, result: SearchResult) -> str:
        """Get metadata string for the search result."""
        parts = []
        if hasattr(result, "play_title") and result.play_title:
            parts.append(f"Play: {result.play_title}")
        if hasattr(result, "act_name") and result.act_name:
            parts.append(f"Act: {result.act_name}")
        if hasattr(result, "scene_name") and result.scene_name:
            parts.append(f"Scene: {result.scene_name}")
        return " | ".join(parts)

    def _get_text_snippet(self, result: SearchResult) -> str:
        """Get the text snippet, using highlight if available."""
        # Check for highlighted content first
        if hasattr(result, "highlighted") and result.highlighted:
            if isinstance(result.highlighted, list):
                return " ... ".join(result.highlighted)
            return str(result.highlighted)

        # Fall back to regular text
        if hasattr(result, "text") and result.text:
            text = strip_tags(str(result.text))
            if len(text) > self.max_text_length:
                text = text[: self.max_text_length].rsplit(" ", 1)[0] + "..."
            return text

        return ""


class SearchResultsHeader(HorizontalLayoutBlock):
    """
    Header for the search results listing showing count.

    Args:
        results: The Haystack search queryset containing search results.

    """

    name: str = "search-results__title"
    justify: str = "between"

    def __init__(self, results: SearchQuerySet, **kwargs):
        super().__init__(**kwargs)
        count = results.count() if results else 0
        self.add_block(
            Block(
                f"Search Results: {count}",
                css_class="fs-5 font-bold mb-3",
            )
        )


class PagedSearchResultsBlock(PagedModelWidget):
    """
    Paginated listing of search results.

    Args:
        results: The Haystack search queryset containing search results.
        query: The search query text.

    Keyword Args:
        facets: Dictionary of facet names to selected values.

    """

    page_kwarg: str = "p"
    paginate_by: int = 10
    model_widget: Block = SearchResultBlock

    def __init__(
        self,
        results: SearchQuerySet,
        query: str | None,
        facets: dict[str, list[str]] | None = None,
        **kwargs,
    ):
        if query is not None:
            kwargs["extra_url"] = {"q": query}
            if facets:
                for key, value in facets.items():
                    kwargs["extra_url"][key] = ",".join(value)
        super().__init__(queryset=results, **kwargs)


class FacetBlock(Block):
    """
    Base class for facet filtering blocks.

    Displays facet values with counts and filter buttons.
    Subclass this to create facet blocks for specific fields.

    Args:
        results: The Haystack search queryset containing search results.
        query: The search query text.

    """

    #: The model class for this facet
    model: type[Model]
    #: The title for this block
    title: str
    #: The facet field name
    facet: str
    #: The model field to filter by
    model_field: str
    #: URL name for the search view
    search_url_name: str = "core:search"

    def __init__(self, results: SearchQuerySet, query: str | None, **kwargs):
        self.query = query
        super().__init__(**kwargs)
        self.add_class("border")
        self.add_class("bg-white")
        self.add_class("rounded")

        self.add_block(Block(self.title, tag="h5", css_class="p-3 border-bottom"))

        if results is None:
            self.add_block(Block("No results", css_class="p-3 text-muted"))
            return

        try:
            facet_qs = results.facet(self.facet)
            stats = facet_qs.facet_counts()
            facet_data = stats.get("fields", {}).get(self.facet, [])
        except Exception:  # noqa: BLE001
            facet_data = []

        if not facet_data:
            self.add_block(Block("No facets available", css_class="p-3 text-muted"))
            return

        body = Block(name="list-group", css_class="list-group-flush")
        for identifier, count in facet_data[:10]:  # Limit to top 10
            body.add_block(
                Block(
                    HorizontalLayoutBlock(
                        Block(str(identifier), css_class="fs-6"),
                        HorizontalLayoutBlock(
                            TagBlock(count, color="cyan", css_class="me-2"),
                            LinkButton(
                                text="Filter",
                                url=reverse(self.search_url_name)
                                + f"?q={query or ''}&{self.facet}={identifier}",
                                color="outline-secondary",
                                size="sm",
                            ),
                        ),
                    ),
                    tag="li",
                    name="list-group-item",
                    css_class="p-2",
                )
            )
        self.add_block(body)


class SearchResultsSpeakerFacet(FacetBlock):
    """Facet block for filtering by speaker name."""

    model: type[Model] = Speaker
    title: str = "Speakers"
    facet: str = "speaker_name"
    model_field: str = "name"


class SearchResultsPlayFacet(FacetBlock):
    """Facet block for filtering by play title."""

    model: type[Model] = Play
    title: str = "Plays"
    facet: str = "play_title"
    model_field: str = "title"


class SearchResultsActFacet(FacetBlock):
    """Facet block for filtering by act name."""

    title: str = "Acts"
    facet: str = "act_name"
    model_field: str = "name"


class SearchResultsSceneFacet(FacetBlock):
    """Facet block for filtering by scene name."""

    title: str = "Scenes"
    facet: str = "scene_name"
    model_field: str = "name"


class SearchResultsPageHeader(Block):
    """
    Page header for search results showing query and active filters.

    Args:
        query: The search query text.

    Keyword Args:
        facets: Active facet filters as dict of facet name to values.

    """

    block: str = "search-results__header"
    css_class: str = "mb-4"

    def __init__(
        self,
        query: str | None,
        facets: dict[str, list[str]] | None = None,
        **kwargs,
    ):
        if facets is None:
            facets = {}
        super().__init__(**kwargs)

        self.add_block(
            Block(
                "Search Results",
                tag="h2",
                name="search-results__header__title",
            )
        )

        if query:
            self.add_block(
                Block(
                    f'Query: "{query}"',
                    name="search-results__header__subtitle",
                    css_class="text-muted fs-6",
                )
            )

        if facets:
            filter_row = HorizontalLayoutBlock(
                Block("Active Filters:", css_class="me-3 fw-bold"),
                justify="start",
                align="center",
                css_class="mt-3",
            )
            for facet_name, values in facets.items():
                for value in values:
                    filter_row.add_block(
                        LinkButton(
                            text=f"{facet_name}: {value} ✕",
                            url=reverse("core:search") + f"?q={query or ''}",
                            color="outline-secondary",
                            size="sm",
                            css_class="me-2",
                        )
                    )
            self.add_block(filter_row)


class PagedSearchLayout(Block):
    """
    Main layout for search results page with facets.

    Args:
        results: The Haystack search queryset containing search results.
        query: The search query text.

    Keyword Args:
        facets: Active facet filters.
        show_facets: Whether to show facet blocks (default True).

    """

    name: str = "search-layout"
    modifier: str = "paged"

    def __init__(
        self,
        results: SearchQuerySet,
        query: str | None = None,
        facets: dict[str, list[str]] | None = None,
        show_facets: bool = True,
        **kwargs,
    ):
        self.query = query
        if facets is None:
            facets = {}
        super().__init__(**kwargs)

        self.add_block(SearchResultsPageHeader(query, facets=facets))
        self.add_block(SearchResultsHeader(results))

        row = Row()

        # Results column
        results_width = 8 if show_facets else 12
        row.add_column(
            Column(
                PagedSearchResultsBlock(results, query, facets=facets),
                name="results",
                base_width=results_width,
            )
        )

        # Facets column
        if show_facets:
            row.add_column(
                Column(
                    SearchResultsSpeakerFacet(results, query, css_class="mb-3"),
                    SearchResultsPlayFacet(results, query, css_class="mb-3"),
                    SearchResultsActFacet(results, query, css_class="mb-3"),
                    SearchResultsSceneFacet(results, query),
                    name="facets",
                    base_width=4,
                )
            )

        self.add_block(row)


# -----------------------------------------------------------------------------
# More Like This Widgets
# -----------------------------------------------------------------------------


class MoreLikeThisResultsWidget(Block):
    """
    Widget for displaying more_like_this results.

    Args:
        results: The search results from more_like_this.
        source_object: The object that was used as the source.

    """

    name: str = "more-like-this-results"

    def __init__(
        self,
        results: list | None = None,
        source_object: Any = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if source_object:
            self.add_block(
                Block(
                    f"Documents similar to: {source_object}",
                    tag="h4",
                    css_class="mb-3",
                )
            )

        if not results:
            self.add_block(Block("No similar documents found.", css_class="text-muted"))
            return

        self.add_block(
            Block(f"Found {len(results)} similar documents", css_class="mb-3")
        )

        for result in results:
            self.add_block(SearchResultBlock(object=result))


# -----------------------------------------------------------------------------
# Index Management Widgets
# -----------------------------------------------------------------------------


class IndexManagementWidget(CardWidget):
    """
    Widget for index management operations.

    Displays status information about the search index and
    provides an interface for management operations.
    """

    title: str = "Index Management"
    icon: str = "database"
    name: str = "index-management"

    def __init__(
        self,
        message: str | None = None,
        success: bool = True,
        form: Form | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        content = Block()

        if message:
            alert_class = "alert-success" if success else "alert-danger"
            content.add_block(
                Block(
                    message,
                    css_class=f"alert {alert_class}",
                )
            )

        content.add_block(
            Block(
                "Use the form below to manage the search index. "
                "Be careful with destructive operations!",
                css_class="text-muted mb-3",
            )
        )
        content.add_block(
            CrispyFormWidget(form=form, css_class="mb-3"),
        )
        self.set_widget(content)


# -----------------------------------------------------------------------------
# Filter Examples Widget
# -----------------------------------------------------------------------------


class FilterExamplesWidget(Block):
    """
    Widget showing examples of filter results.

    Args:
        filter_type: The type of filter applied.
        field: The field being filtered.
        value: The filter value.
        results: The search results.

    """

    name: str = "filter-examples"

    def __init__(
        self,
        filter_type: str | None = None,
        field: str | None = None,
        value: str | None = None,
        results: SearchQuerySet | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if filter_type and field and value:
            self.add_block(
                Block(
                    f"Filter: {field} {filter_type} '{value}'",
                    tag="h4",
                    css_class="mb-3",
                )
            )

            count = results.count() if results else 0
            self.add_block(Block(f"Found {count} results", css_class="mb-3 text-muted"))

            if results:
                for result in results[:10]:  # Limit to 10 results
                    self.add_block(SearchResultBlock(object=result))
        else:
            self.add_block(
                Block(
                    "Select a filter type, field, and value to see results.",
                    css_class="text-muted",
                )
            )


# -----------------------------------------------------------------------------
# Sorting Options Widget
# -----------------------------------------------------------------------------


class SortingOptionsWidget(Block):
    """
    Widget showing sorted results.

    Args:
        sort_field: The field to sort by.
        sort_direction: 'asc' or 'desc'.
        results: The sorted search results.

    """

    name: str = "sorting-options"

    def __init__(
        self,
        sort_field: str | None = None,
        sort_direction: str = "asc",
        results: SearchQuerySet | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if sort_field:
            direction_label = "ascending" if sort_direction == "asc" else "descending"
            self.add_block(
                Block(
                    f"Sorted by: {sort_field} ({direction_label})",
                    tag="h4",
                    css_class="mb-3",
                )
            )

        count = results.count() if results else 0
        self.add_block(Block(f"Found {count} results", css_class="mb-3 text-muted"))

        if results:
            for result in results[:20]:  # Limit to 20 results
                self.add_block(SearchResultBlock(object=result))


# -----------------------------------------------------------------------------
# Pagination Widget
# -----------------------------------------------------------------------------


class PaginationInfoWidget(Block):
    """
    Widget showing pagination information.

    Args:
        page: Current page number.
        page_size: Number of results per page.
        total_count: Total number of results.
        results: The paginated search results.

    """

    name: str = "pagination-info"

    def __init__(
        self,
        page: int = 1,
        page_size: int = 10,
        total_count: int = 0,
        results: list | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        start = (page - 1) * page_size + 1
        end = min(page * page_size, total_count)
        total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0

        self.add_block(
            Block(
                f"Showing {start}-{end} of {total_count} results "
                f"(Page {page} of {total_pages})",
                css_class="mb-3 text-muted",
            )
        )

        if results:
            for result in results:
                self.add_block(SearchResultBlock(object=result))
