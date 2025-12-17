"""
Forms for the demo application.

This module provides forms for searching, filtering, and managing the search index,
following patterns from django-sphinx-hosting.
"""

from typing import ClassVar

from crispy_forms.bootstrap import FieldWithButtons
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Field, Fieldset, Layout, Submit
from django import forms
from django.urls import reverse_lazy
from haystack.forms import FacetedSearchForm, SearchForm

from demo.core.models import Play, Speaker, Speech


class BasicSearchForm(SearchForm):
    """
    Basic search form extending haystack's SearchForm.

    Similar to GlobalSearchForm in django-sphinx-hosting, this provides
    a simple text search field with crispy-forms styling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal px-3"
        self.helper.form_method = "get"
        self.helper.form_show_labels = False
        self.helper.form_action = reverse_lazy("core:search")
        self.helper.layout = Layout(
            FieldWithButtons(
                Field("q", css_class="text-dark", placeholder="Search speeches..."),
                HTML(
                    '<button type="submit" class="btn btn-primary">'
                    '<span class="bi bi-search"></span> Search</button>'
                ),
            )
        )


class AdvancedSearchForm(FacetedSearchForm):
    """
    Advanced search form with full-featured search options.

    Provides:

    - Query text field
    - Model selection (Speech, Speaker, Play)
    - Sort options (field and direction)
    - Highlight checkbox
    - Pagination fields (page size)
    - Field selection checkboxes
    """

    SORT_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("", "Relevance (default)"),
        ("speaker_name", "Speaker Name (A-Z)"),
        ("-speaker_name", "Speaker Name (Z-A)"),
        ("play_title", "Play Title (A-Z)"),
        ("-play_title", "Play Title (Z-A)"),
        ("created_date", "Date (oldest first)"),
        ("-created_date", "Date (newest first)"),
        ("order", "Order (ascending)"),
        ("-order", "Order (descending)"),
    ]

    MODEL_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("", "All Models"),
        ("core.speech", "Speeches"),
        ("core.speaker", "Speakers"),
        ("core.play", "Plays"),
    ]

    PAGE_SIZE_CHOICES: ClassVar[list[tuple[int, str]]] = [
        (10, "10 results"),
        (25, "25 results"),
        (50, "50 results"),
        (100, "100 results"),
    ]

    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        label="Sort by",
    )

    models = forms.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        label="Search in",
    )

    highlight = forms.BooleanField(
        required=False,
        initial=True,
        label="Highlight results",
    )

    page_size = forms.ChoiceField(
        choices=PAGE_SIZE_CHOICES,
        required=False,
        initial=10,
        label="Results per page",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:advanced-search")
        self.helper.layout = Layout(
            Fieldset(
                "Search Options",
                Field("q", placeholder="Enter search terms..."),
                Field("models"),
                Field("sort_by"),
                Div(
                    Field("highlight"),
                    Field("page_size"),
                    css_class="row",
                ),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class FilterSearchForm(forms.Form):
    """
    Form for testing query filters.

    Allows testing all filter types:

    - contains, startswith, endswith, exact
    - gt, gte, lt, lte
    - fuzzy, in, range
    """

    FILTER_TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("contains", "Contains (*value*)"),
        ("startswith", "Starts with (value*)"),
        ("endswith", "Ends with (*value)"),
        ("exact", "Exact match"),
        ("gt", "Greater than (>)"),
        ("gte", "Greater than or equal (>=)"),
        ("lt", "Less than (<)"),
        ("lte", "Less than or equal (<=)"),
        ("fuzzy", "Fuzzy match (~)"),
        ("in", "In list (value1,value2,...)"),
        ("range", "Range (start,end)"),
    ]

    FIELD_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("text", "Speech Text"),
        ("speaker_name", "Speaker Name"),
        ("act_name", "Act Name"),
        ("scene_name", "Scene Name"),
        ("play_title", "Play Title"),
        ("order", "Order (integer)"),
        ("speech_length", "Speech Length (float)"),
        ("is_soliloquy", "Is Soliloquy (boolean)"),
    ]

    filter_type = forms.ChoiceField(
        choices=FILTER_TYPE_CHOICES,
        label="Filter Type",
    )

    field = forms.ChoiceField(
        choices=FIELD_CHOICES,
        label="Field",
    )

    value = forms.CharField(
        label="Value",
        help_text=(
            "For 'in' filter, use comma-separated values. "
            "For 'range', use comma-separated start,end."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:filter-examples")
        self.helper.layout = Layout(
            Fieldset(
                "Filter Options",
                Field("filter_type"),
                Field("field"),
                Field("value"),
            ),
            ButtonHolder(
                Submit("submit", "Apply Filter", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class FacetSearchForm(FacetedSearchForm):
    """
    Form for testing facet functionality.

    Provides options for:
    - Regular facets
    - Date facets
    - Query facets
    """

    FACET_FIELD_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("speaker_name", "Speaker Name"),
        ("act_name", "Act Name"),
        ("scene_name", "Scene Name"),
        ("play_title", "Play Title"),
    ]

    DATE_FACET_GAP_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("day", "Day"),
        ("week", "Week"),
        ("month", "Month"),
        ("year", "Year"),
    ]

    facet_fields = forms.MultipleChoiceField(
        choices=FACET_FIELD_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Facet Fields",
        initial=["speaker_name", "play_title"],
    )

    enable_date_facets = forms.BooleanField(
        required=False,
        initial=False,
        label="Enable Date Facets",
    )

    date_facet_gap = forms.ChoiceField(
        choices=DATE_FACET_GAP_CHOICES,
        required=False,
        initial="month",
        label="Date Facet Interval",
    )

    query_facet = forms.CharField(
        required=False,
        label="Query Facet",
        help_text="Enter a query string for a query facet (e.g., 'speaker_name:KING')",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:facets")
        self.helper.layout = Layout(
            Fieldset(
                "Search",
                Field("q", placeholder="Enter search terms..."),
            ),
            Fieldset(
                "Facet Options",
                Field("facet_fields"),
                Field("enable_date_facets"),
                Field("date_facet_gap"),
                Field("query_facet"),
            ),
            ButtonHolder(
                Submit("submit", "Search with Facets", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class MoreLikeThisForm(forms.Form):
    """
    Form for testing more_like_this functionality.

    Allows selecting an object and finding similar documents.
    """

    MODEL_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("speech", "Speech"),
        ("speaker", "Speaker"),
        ("play", "Play"),
    ]

    model_type = forms.ChoiceField(
        choices=MODEL_CHOICES,
        label="Object Type",
    )

    object_id = forms.IntegerField(
        label="Object ID",
        help_text="Enter the ID of the object to find similar documents for.",
    )

    additional_query = forms.CharField(
        required=False,
        label="Additional Query",
        help_text="Optional: Additional query string to filter results.",
    )

    limit_models = forms.MultipleChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Limit to Models",
        help_text="Optional: Limit results to specific model types.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:more-like-this")
        self.helper.layout = Layout(
            Fieldset(
                "Source Object",
                Field("model_type"),
                Field("object_id"),
            ),
            Fieldset(
                "Options",
                Field("additional_query"),
                Field("limit_models"),
            ),
            ButtonHolder(
                Submit("submit", "Find Similar", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )

    def get_model_instance(self):
        """
        Get the model instance based on form data.

        Returns:
            The model instance or None if not found.

        """
        model_type = self.cleaned_data.get("model_type")
        object_id = self.cleaned_data.get("object_id")

        if not model_type or not object_id:
            return None

        model_map = {
            "speech": Speech,
            "speaker": Speaker,
            "play": Play,
        }

        model_class = model_map.get(model_type)
        if model_class:
            try:
                return model_class.objects.get(pk=object_id)
            except model_class.DoesNotExist:
                return None
        return None


class IndexManagementForm(forms.Form):
    """
    Form for testing remove/clear operations.

    Allows:

    - Removing a specific document
    - Clearing all documents
    - Clearing documents for a specific model
    """

    ACTION_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("remove", "Remove Document"),
        ("clear_all", "Clear All Documents"),
        ("clear_model", "Clear Model Documents"),
        ("rebuild", "Rebuild Index"),
    ]

    MODEL_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("speech", "Speech"),
        ("speaker", "Speaker"),
        ("play", "Play"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Action",
    )

    model_type = forms.ChoiceField(
        choices=MODEL_CHOICES,
        required=False,
        label="Model Type",
        help_text="Required for 'Remove Document' and 'Clear Model' actions.",
    )

    object_id = forms.IntegerField(
        required=False,
        label="Object ID",
        help_text="Required for 'Remove Document' action.",
    )

    commit = forms.BooleanField(
        required=False,
        initial=True,
        label="Commit Changes",
        help_text=(
            "If checked, changes will be committed (index refreshed) immediately."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "post"
        self.helper.form_action = reverse_lazy("core:index-management")
        self.helper.layout = Layout(
            Fieldset(
                "Index Management",
                Field("action"),
                Field("model_type"),
                Field("object_id"),
                Field("commit"),
            ),
            ButtonHolder(
                Submit("submit", "Execute", css_class="btn btn-danger"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )

    def clean(self):
        """Validate form data based on action."""
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        model_type = cleaned_data.get("model_type")
        object_id = cleaned_data.get("object_id")

        if action == "remove":
            if not model_type:
                self.add_error(
                    "model_type", "Model type is required for remove action."
                )
            if not object_id:
                self.add_error("object_id", "Object ID is required for remove action.")

        if action == "clear_model":
            if not model_type:
                self.add_error(
                    "model_type", "Model type is required for clear model action."
                )

        return cleaned_data


class SortingForm(forms.Form):
    """Form for demonstrating sorting functionality."""

    SORT_FIELD_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("speaker_name", "Speaker Name"),
        ("play_title", "Play Title"),
        ("act_name", "Act Name"),
        ("scene_name", "Scene Name"),
        ("order", "Speech Order"),
        ("created_date", "Created Date"),
        ("speech_length", "Speech Length"),
    ]

    SORT_DIRECTION_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("asc", "Ascending"),
        ("desc", "Descending"),
    ]

    q = forms.CharField(
        required=False,
        label="Search Query",
        initial="*:*",
    )

    sort_field = forms.ChoiceField(
        choices=SORT_FIELD_CHOICES,
        label="Sort Field",
    )

    sort_direction = forms.ChoiceField(
        choices=SORT_DIRECTION_CHOICES,
        initial="asc",
        label="Sort Direction",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:sorting")
        self.helper.layout = Layout(
            Fieldset(
                "Sorting Options",
                Field("q"),
                Field("sort_field"),
                Field("sort_direction"),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class HighlightingForm(forms.Form):
    """Form for demonstrating highlighting functionality."""

    q = forms.CharField(
        label="Search Query",
        help_text="Enter search terms to highlight in results.",
    )

    highlight = forms.BooleanField(
        required=False,
        initial=True,
        label="Enable Highlighting",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:highlighting")
        self.helper.layout = Layout(
            Fieldset(
                "Highlighting Options",
                Field("q"),
                Field("highlight"),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class PaginationForm(forms.Form):
    """Form for demonstrating pagination functionality."""

    q = forms.CharField(
        required=False,
        label="Search Query",
        initial="*:*",
    )

    page_size = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=10,
        label="Page Size",
    )

    page = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Page Number",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:pagination")
        self.helper.layout = Layout(
            Fieldset(
                "Pagination Options",
                Field("q"),
                Field("page_size"),
                Field("page"),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class SpellingForm(forms.Form):
    """Form for demonstrating spelling suggestions."""

    q = forms.CharField(
        label="Search Query",
        help_text="Enter a misspelled query to see spelling suggestions.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:spelling")
        self.helper.layout = Layout(
            Fieldset(
                "Spelling Suggestions",
                Field("q", placeholder="Enter query (try misspelling something)..."),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )


class FieldSelectionForm(forms.Form):
    """Form for demonstrating field selection functionality."""

    FIELD_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("text", "Speech Text"),
        ("speaker_name", "Speaker Name"),
        ("act_name", "Act Name"),
        ("scene_name", "Scene Name"),
        ("play_title", "Play Title"),
        ("order", "Order"),
        ("created_date", "Created Date"),
        ("speech_length", "Speech Length"),
        ("is_soliloquy", "Is Soliloquy"),
    ]

    q = forms.CharField(
        required=False,
        label="Search Query",
        initial="*:*",
    )

    fields = forms.MultipleChoiceField(
        choices=FIELD_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Fields to Return",
        initial=["text", "speaker_name", "play_title"],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_method = "get"
        self.helper.form_action = reverse_lazy("core:field-selection")
        self.helper.layout = Layout(
            Fieldset(
                "Field Selection",
                Field("q"),
                Field("fields"),
            ),
            ButtonHolder(
                Submit("submit", "Search", css_class="btn btn-primary"),
                css_class="d-flex flex-row justify-content-end",
            ),
        )
