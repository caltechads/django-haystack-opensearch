"""
URL configuration for the demo core app.

This module defines URL patterns for all demo views including search,
filtering, facets, and index management functionality.
"""

from typing import Final

from django.urls import path

from .views import (
    AdvancedSearchView,
    FacetsView,
    FieldSelectionView,
    FilterExamplesView,
    HighlightingView,
    IndexManagementView,
    IndexStatusView,
    MoreLikeThisView,
    PaginationView,
    PlayListView,
    SearchView,
    SortingView,
    SpecialCasesView,
    SpellingView,
)

# These URLs are loaded by demo/urls.py.
app_name: Final[str] = "core"

urlpatterns = [
    # Home page
    path("", PlayListView.as_view(), name="home"),
    # Search views
    path("search/", SearchView.as_view(), name="search"),
    path("search/advanced/", AdvancedSearchView.as_view(), name="advanced-search"),
    # Feature demonstration views
    path("filters/", FilterExamplesView.as_view(), name="filter-examples"),
    path("facets/", FacetsView.as_view(), name="facets"),
    path("more-like-this/", MoreLikeThisView.as_view(), name="more-like-this"),
    path("sorting/", SortingView.as_view(), name="sorting"),
    path("highlighting/", HighlightingView.as_view(), name="highlighting"),
    path("pagination/", PaginationView.as_view(), name="pagination"),
    path("spelling/", SpellingView.as_view(), name="spelling"),
    path("field-selection/", FieldSelectionView.as_view(), name="field-selection"),
    path("special-cases/", SpecialCasesView.as_view(), name="special-cases"),
    # Index management views
    path("index/", IndexStatusView.as_view(), name="index-status"),
    path("index/manage/", IndexManagementView.as_view(), name="index-management"),
]
