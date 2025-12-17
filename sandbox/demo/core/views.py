"""
Views for the demo application.

This module provides views for demonstrating django-haystack-opensearch functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from braces.views import LoginRequiredMixin, MessageMixin
from django.contrib import messages
from django.urls import reverse
from django.views.generic import FormView, TemplateView
from haystack import connections
from haystack.generic_views import SearchView as HaystackSearchView
from haystack.query import SearchQuerySet
from wildewidgets import (
    Block,
    BreadcrumbBlock,
    CardWidget,
    CrispyFormWidget,
    Navbar,
    NavbarMixin,
    StandardWidgetMixin,
)

from .forms import (
    AdvancedSearchForm,
    BasicSearchForm,
    FacetSearchForm,
    FieldSelectionForm,
    FilterSearchForm,
    HighlightingForm,
    IndexManagementForm,
    MoreLikeThisForm,
    PaginationForm,
    SortingForm,
    SpellingForm,
)
from .models import Play, Speaker, Speech
from .search_indexes import reindex_all
from .wildewidgets import (
    Breadcrumbs,
    FilterExamplesWidget,
    IndexManagementWidget,
    MoreLikeThisResultsWidget,
    NavigationSidebar,
    PagedSearchLayout,
    PaginationInfoWidget,
    PlayTableWidget,
    SearchResultBlock,
    SortingOptionsWidget,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from haystack.forms import ModelSearchForm


class DemoStandardMixin(LoginRequiredMixin, StandardWidgetMixin, NavbarMixin):
    """
    Standard mixin for demo views.

    Provides common functionality for all demo views including:
    - Navigation sidebar
    """

    template_name: ClassVar[str] = "core/intermediate.html"
    navbar_class: ClassVar[Navbar] = NavigationSidebar


class PlayListView(DemoStandardMixin, TemplateView):
    """
    View displaying a list of all plays.

    This is the home page for the demo application, showing all available
    plays in a table format. Users can see play titles and created dates.
    """

    def get_content(self) -> Block:
        """
        Get the main content widget for the page.

        Returns:
            PlayTableWidget displaying all plays.

        """
        return PlayTableWidget()

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """
        Get the breadcrumbs for the page.

        Returns:
            Breadcrumbs starting from the demo home.

        """
        return Breadcrumbs()


# =============================================================================
# Search Views
# =============================================================================


class SearchView(
    MessageMixin,
    DemoStandardMixin,
    HaystackSearchView,
):
    """
    Main search view for the demo application.

    Provides full-text search with facet filtering, following the
    GlobalSphinxPageSearchView pattern from django-sphinx-hosting.
    """

    #: The navbar class for the search.
    navbar_class: ClassVar[Navbar] = NavigationSidebar
    #: The form class for the search.
    form_class: ClassVar[type[ModelSearchForm]] = BasicSearchForm
    #: The query for the search.
    query: str | None = None
    #: The facets for the search.
    facets: dict[str, list[str]]

    def form_invalid(self, form: ModelSearchForm) -> HttpResponse:  # noqa: ARG002
        """
        Handle invalid form submission.

        Args:
            form: The form that was invalid.

        Returns:
            HttpResponse: The response to the request.

        """
        self.queryset = self.get_queryset()
        self.object_list = self.queryset
        self.query = None
        self.facets = {}
        context = self.get_context_data()
        return self.render_to_response(context)

    def form_valid(self, form: ModelSearchForm) -> HttpResponse:
        """
        Handle valid form submission with facet filtering.

        Args:
            form: The form that was valid.

        Returns:
            HttpResponse: The response to the request.

        """
        self.queryset = form.search()
        self.facets = {}

        # Extract facets from GET parameters
        if speaker_name := self.request.GET.get("speaker_name"):
            self.queryset = self.queryset.filter(speaker_name__exact=speaker_name)
            self.facets["speaker_name"] = [speaker_name]
        if play_title := self.request.GET.get("play_title"):
            self.queryset = self.queryset.filter(play_header_text__exact=play_title)
            self.facets["play_title"] = [play_title]
        if act_name := self.request.GET.get("act_name"):
            self.queryset = self.queryset.filter(act_name__exact=act_name)
            self.facets["act_name"] = [act_name]
        if scene_name := self.request.GET.get("scene_name"):
            self.queryset = self.queryset.filter(scene_name__exact=scene_name)
            self.facets["scene_name"] = [scene_name]

        self.object_list = self.queryset
        self.query = form.cleaned_data.get(self.search_field, "")
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_content(self) -> Block:
        """Return the main content widget."""
        return PagedSearchLayout(self.object_list, self.query, facets=self.facets)

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs for search results."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Search")
        if self.query:
            breadcrumbs.add_breadcrumb(f'Query: "{self.query}"')
        return breadcrumbs


class AdvancedSearchView(DemoStandardMixin, TemplateView):
    """
    Advanced search view with more options.

    Demonstrates sorting, highlighting, model filtering, and pagination.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = AdvancedSearchForm(request.GET or None)
        self.results = None
        self.query = None

        if self.form.is_valid() and self.form.cleaned_data.get("q"):
            self.query = self.form.cleaned_data["q"]
            sqs = SearchQuerySet().filter(content=self.query)

            # Apply model filter
            if model := self.form.cleaned_data.get("models"):
                if model == "core.speech":
                    sqs = sqs.models(Speech)
                elif model == "core.speaker":
                    sqs = sqs.models(Speaker)
                elif model == "core.play":
                    sqs = sqs.models(Play)

            # Apply sorting
            if sort_by := self.form.cleaned_data.get("sort_by"):
                sqs = sqs.order_by(sort_by)

            # Apply highlighting
            if self.form.cleaned_data.get("highlight"):
                sqs = sqs.highlight()

            self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Advanced Search")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                Block(f"Found {self.results.count()} results", css_class="mt-4 mb-3")
            )
            for result in self.results[:20]:
                content.add_block(SearchResultBlock(object=result))

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Advanced Search")
        return breadcrumbs


class FilterExamplesView(DemoStandardMixin, TemplateView):
    """
    View demonstrating all filter types.

    Shows examples of contains, startswith, endswith, exact,
    gt, gte, lt, lte, fuzzy, in, and range filters.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = FilterSearchForm(request.GET or None)
        self.results = None
        self.filter_type = None
        self.field = None
        self.value = None

        if self.form.is_valid():
            self.filter_type = self.form.cleaned_data["filter_type"]
            self.field = self.form.cleaned_data["field"]
            self.value = self.form.cleaned_data["value"]

            sqs = SearchQuerySet()

            # Build the filter based on type
            filter_key = f"{self.field}__{self.filter_type}"
            if self.filter_type == "in":
                # Parse comma-separated values for 'in' filter
                values = [v.strip() for v in self.value.split(",")]
                sqs = sqs.filter(**{filter_key: values})
            elif self.filter_type == "range":
                # Parse comma-separated start,end for 'range' filter
                parts = self.value.split(",")
                if len(parts) == 2:  # noqa: PLR2004
                    sqs = sqs.filter(
                        **{filter_key: (parts[0].strip(), parts[1].strip())}
                    )
            else:
                sqs = sqs.filter(**{filter_key: self.value})

            self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Filter Examples")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                FilterExamplesWidget(
                    filter_type=self.filter_type,
                    field=self.field,
                    value=self.value,
                    results=self.results,
                )
            )

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Filter Examples")
        return breadcrumbs


class FacetsView(DemoStandardMixin, TemplateView):
    """
    View demonstrating facet functionality.

    Shows regular facets, date facets, and query facets.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = FacetSearchForm(request.GET or None)
        self.results = None
        self.query = None
        self.facet_counts = {}

        if self.form.is_valid():
            self.query = self.form.cleaned_data.get("q", "*:*") or "*:*"
            sqs = SearchQuerySet().filter(content=self.query)

            # Apply facets
            facet_fields = self.form.cleaned_data.get("facet_fields", [])
            for facet_field in facet_fields:
                sqs = sqs.facet(facet_field)

            # Get facet counts
            if facet_fields:
                self.facet_counts = sqs.facet_counts()

            self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Facet Search")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results and facets
        if self.results is not None:
            content.add_block(
                Block(f"Found {self.results.count()} results", css_class="mt-4 mb-3")
            )

            # Show facet counts
            if self.facet_counts:
                facet_block = Block(tag="div", css_class="mb-4")
                facet_block.add_block(Block("Facet Counts:", tag="h5"))
                fields = self.facet_counts.get("fields", {})
                for field_name, counts in fields.items():
                    facet_block.add_block(Block(f"{field_name}:", tag="h6"))
                    for value, count in counts[:10]:
                        facet_block.add_block(
                            Block(f"  - {value}: {count}", css_class="ms-3")
                        )
                content.add_block(facet_block)

            # Show results
            for result in self.results[:10]:
                content.add_block(SearchResultBlock(object=result))

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Facets")
        return breadcrumbs


class MoreLikeThisView(DemoStandardMixin, TemplateView):
    """
    View demonstrating more_like_this functionality.

    Finds documents similar to a selected document.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = MoreLikeThisForm(request.GET or None)
        self.results = None
        self.source_object = None

        if self.form.is_valid():
            self.source_object = self.form.get_model_instance()

            if self.source_object:
                backend = connections["default"].get_backend()
                additional_query = self.form.cleaned_data.get("additional_query")

                try:
                    result = backend.more_like_this(
                        self.source_object,
                        additional_query_string=additional_query or None,
                    )
                    self.results = result.get("results", [])
                except Exception as e:  # noqa: BLE001
                    messages.error(request, f"Error finding similar documents: {e}")
            else:
                messages.warning(request, "Object not found.")

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="More Like This")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        content.add_block(
            MoreLikeThisResultsWidget(
                results=self.results,
                source_object=self.source_object,
            )
        )

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("More Like This")
        return breadcrumbs


class SortingView(DemoStandardMixin, TemplateView):
    """
    View demonstrating sorting functionality.

    Shows how to sort search results by different fields.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = SortingForm(request.GET or None)
        self.results = None
        self.sort_field = None
        self.sort_direction = "asc"

        if self.form.is_valid():
            query = self.form.cleaned_data.get("q", "*:*") or "*:*"
            self.sort_field = self.form.cleaned_data["sort_field"]
            self.sort_direction = self.form.cleaned_data["sort_direction"]

            sqs = SearchQuerySet().filter(content=query)

            # Apply sorting
            if self.sort_direction == "desc":
                sqs = sqs.order_by(f"-{self.sort_field}")
            else:
                sqs = sqs.order_by(self.sort_field)

            self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Sorting")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                SortingOptionsWidget(
                    sort_field=self.sort_field,
                    sort_direction=self.sort_direction,
                    results=self.results,
                )
            )

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Sorting")
        return breadcrumbs


class HighlightingView(DemoStandardMixin, TemplateView):
    """
    View demonstrating highlighting functionality.

    Shows how search terms are highlighted in results.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = HighlightingForm(request.GET or None)
        self.results = None
        self.query = None

        if self.form.is_valid():
            self.query = self.form.cleaned_data.get("q")
            if self.query:
                sqs = SearchQuerySet().filter(content=self.query)

                # Apply highlighting if enabled
                if self.form.cleaned_data.get("highlight", True):
                    sqs = sqs.highlight()

                self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Highlighting")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                Block(f"Found {self.results.count()} results", css_class="mt-4 mb-3")
            )
            for result in self.results[:10]:
                content.add_block(SearchResultBlock(object=result))

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Highlighting")
        return breadcrumbs


class PaginationView(DemoStandardMixin, TemplateView):
    """
    View demonstrating pagination functionality.

    Shows how to paginate search results with start_offset and end_offset.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = PaginationForm(request.GET or None)
        self.results = None
        self.page = 1
        self.page_size = 10
        self.total_count = 0

        if self.form.is_valid():
            query = self.form.cleaned_data.get("q", "*:*") or "*:*"
            self.page = self.form.cleaned_data.get("page", 1)
            self.page_size = self.form.cleaned_data.get("page_size", 10)

            sqs = SearchQuerySet().filter(content=query)
            self.total_count = sqs.count()

            # Apply pagination using slicing
            start = (self.page - 1) * self.page_size
            end = start + self.page_size
            self.results = list(sqs[start:end])

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Pagination")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                PaginationInfoWidget(
                    page=self.page,
                    page_size=self.page_size,
                    total_count=self.total_count,
                    results=self.results,
                )
            )

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Pagination")
        return breadcrumbs


class SpellingView(DemoStandardMixin, TemplateView):
    """
    View demonstrating spelling suggestions.

    Shows how to get spelling suggestions for misspelled queries.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = SpellingForm(request.GET or None)
        self.results = None
        self.query = None
        self.suggestion = None

        if self.form.is_valid():
            self.query = self.form.cleaned_data.get("q")
            if self.query:
                # Note: Spelling suggestions require the backend to support it
                # and may need include_spelling=True in HAYSTACK_CONNECTIONS
                sqs = SearchQuerySet().filter(content=self.query)
                self.results = sqs

                # Try to get spelling suggestion
                if hasattr(sqs, "spelling_suggestion"):
                    self.suggestion = sqs.spelling_suggestion()

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Spelling Suggestions")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Spelling suggestion
        if self.suggestion:
            content.add_block(
                Block(
                    f'Did you mean: "{self.suggestion}"?',
                    css_class="alert alert-info mt-4",
                )
            )

        # Results
        if self.results is not None:
            content.add_block(
                Block(f"Found {self.results.count()} results", css_class="mt-4 mb-3")
            )
            for result in self.results[:10]:
                content.add_block(SearchResultBlock(object=result))

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Spelling Suggestions")
        return breadcrumbs


class IndexManagementView(DemoStandardMixin, FormView):
    """
    View for index management operations.

    Allows removing documents, clearing the index, and rebuilding.
    """

    form_class = IndexManagementForm

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle GET request.

        Args:
            request: The HTTP request.
            args: The positional arguments.
            kwargs: The keyword arguments.

        Returns:
            HttpResponse: The response to the request.

        """
        self.message = None
        self.success = True
        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle POST request.

        Args:
            request: The HTTP request.
            args: The positional arguments.
            kwargs: The keyword arguments.

        Returns:
            HttpResponse: The response to the request.

        """
        self.message = None
        self.success = True
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: IndexManagementForm) -> HttpResponse:
        """
        Process the index management action.

        Args:
            form: The index management form.

        Returns:
            HttpResponse: The response to the request.

        """
        action = form.cleaned_data["action"]
        model_type = form.cleaned_data.get("model_type")
        object_id = form.cleaned_data.get("object_id")
        commit = form.cleaned_data.get("commit", True)

        backend = connections["default"].get_backend()
        model_map = {
            "speech": Speech,
            "speaker": Speaker,
            "play": Play,
        }

        try:
            if action == "remove":
                model_class = model_map.get(model_type)
                if model_class and object_id:
                    obj = model_class.objects.get(pk=object_id)
                    backend.remove(obj, commit=commit)
                    self.message = f"Removed {model_type} with ID {object_id}"
                    self.success = True

            elif action == "clear_all":
                backend.clear()
                self.message = "Cleared all documents from index"
                self.success = True

            elif action == "clear_model":
                model_class = model_map.get(model_type)
                if model_class:
                    backend.clear(models=[model_class], commit=commit)
                    self.message = f"Cleared all {model_type} documents"
                    self.success = True

            elif action == "rebuild":
                # Trigger a rebuild by clearing and re-indexing

                backend.clear()
                reindex_all()
                self.message = "Index rebuilt successfully"
                self.success = True

        except Exception as e:  # noqa: BLE001
            self.message = f"Error: {e}"
            self.success = False

        return self.render_to_response(self.get_context_data(form=form))

    def get_content(self) -> Block:
        """Return the main content."""
        form = self.get_form()
        return IndexManagementWidget(
            message=getattr(self, "message", None),
            success=getattr(self, "success", True),
            form=form,
        )

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Index Management")
        return breadcrumbs

    def get_success_url(self) -> str:
        """Return URL to redirect to after successful action."""
        return reverse("core:index-management")


class FieldSelectionView(DemoStandardMixin, TemplateView):
    """
    View demonstrating field selection functionality.

    Shows how to request only specific fields in search results.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.form = FieldSelectionForm(request.GET or None)
        self.results = None
        self.selected_fields = []

        if self.form.is_valid():
            query = self.form.cleaned_data.get("q", "*:*") or "*:*"
            self.selected_fields = self.form.cleaned_data.get("fields", [])

            # Note: Field selection is typically handled at the backend level
            # The SearchQuerySet doesn't directly support stored_fields in the
            # same way, but we can demonstrate the concept
            sqs = SearchQuerySet().filter(content=query)
            self.results = sqs

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()

        # Form widget
        form_widget = CrispyFormWidget(form=self.form)
        form_card = CardWidget(header_text="Field Selection")
        form_card.set_widget(form_widget)
        content.add_block(form_card)

        # Results
        if self.results is not None:
            content.add_block(
                Block(
                    f"Selected fields: {', '.join(self.selected_fields)}",
                    css_class="mt-4 mb-3 text-muted",
                )
            )
            content.add_block(
                Block(f"Found {self.results.count()} results", css_class="mb-3")
            )
            for result in self.results[:10]:
                content.add_block(SearchResultBlock(object=result))

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Field Selection")
        return breadcrumbs


class SpecialCasesView(DemoStandardMixin, TemplateView):
    """
    View demonstrating special query cases.

    Shows empty query handling, match all, reserved words, etc.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.examples = []

        # Example 1: Empty query
        empty_results = SearchQuerySet().filter(content="")
        self.examples.append(
            {
                "name": "Empty Query",
                "query": '""',
                "count": empty_results.count(),
                "description": (
                    "An empty query string returns no results or all results depending "
                    "on configuration."
                ),
            }
        )

        # Example 2: Match all query
        all_results = SearchQuerySet().all()
        self.examples.append(
            {
                "name": "Match All (*:*)",
                "query": "*:*",
                "count": all_results.count(),
                "description": "The match-all query returns all indexed documents.",
            }
        )

        # Example 3: Query with reserved words
        reserved_results = SearchQuerySet().filter(content="AND OR NOT")
        self.examples.append(
            {
                "name": "Reserved Words",
                "query": "AND OR NOT",
                "count": reserved_results.count(),
                "description": (
                    "Queries containing reserved words (AND, OR, NOT) are handled "
                    "appropriately."
                ),
            }
        )

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()
        content.add_block(Block("Special Query Cases", tag="h3", css_class="mb-4"))

        for example in self.examples:
            card = CardWidget(header_text=example["name"])
            card_content = Block()
            card_content.add_block(
                Block(f"Query: {example['query']}", css_class="font-monospace mb-2")
            )
            card_content.add_block(
                Block(f"Results: {example['count']}", css_class="mb-2")
            )
            card_content.add_block(
                Block(example["description"], css_class="text-muted")
            )
            card.set_widget(card_content)
            content.add_block(card)

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Special Cases")
        return breadcrumbs


class IndexStatusView(DemoStandardMixin, TemplateView):
    """
    View showing index status and configuration.

    Displays index mapping, field types, document counts, and health status.
    """

    def get(self, request, *args, **kwargs):
        """Handle GET request."""
        self.index_info = {}

        try:
            backend = connections["default"].get_backend()

            # Get document counts
            speech_count = SearchQuerySet().models(Speech).count()
            speaker_count = SearchQuerySet().models(Speaker).count()
            play_count = SearchQuerySet().models(Play).count()

            self.index_info = {
                "index_name": backend.index_name,
                "document_counts": {
                    "Speech": speech_count,
                    "Speaker": speaker_count,
                    "Play": play_count,
                    "Total": speech_count + speaker_count + play_count,
                },
                "setup_complete": backend.setup_complete,
            }

            # Try to get mapping info
            try:
                if hasattr(backend, "existing_mapping"):
                    self.index_info["mapping"] = backend.existing_mapping
            except Exception:  # noqa: BLE001, S110
                pass

        except Exception as e:  # noqa: BLE001
            self.index_info["error"] = str(e)

        return super().get(request, *args, **kwargs)

    def get_content(self) -> Block:
        """Return the main content."""
        content = Block()
        content.add_block(Block("Index Status", tag="h3", css_class="mb-4"))

        if "error" in self.index_info:
            content.add_block(
                Block(
                    f"Error: {self.index_info['error']}",
                    css_class="alert alert-danger",
                )
            )
            return content

        # Index name
        content.add_block(
            Block(
                f"Index Name: {self.index_info.get('index_name', 'Unknown')}",
                css_class="mb-2",
            )
        )

        # Setup status
        setup = self.index_info.get("setup_complete", False)
        status_class = "text-success" if setup else "text-warning"
        content.add_block(
            Block(
                f"Setup Complete: {setup}",
                css_class=f"mb-3 {status_class}",
            )
        )

        # Document counts
        counts = self.index_info.get("document_counts", {})
        count_card = CardWidget(header_text="Document Counts")
        count_content = Block()
        for model, count in counts.items():
            count_content.add_block(Block(f"{model}: {count}", css_class="mb-1"))
        count_card.set_widget(count_content)
        content.add_block(count_card)

        return content

    def get_breadcrumbs(self) -> BreadcrumbBlock:
        """Return breadcrumbs."""
        breadcrumbs = Breadcrumbs()
        breadcrumbs.add_breadcrumb("Index Status")
        return breadcrumbs
