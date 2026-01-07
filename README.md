# django-haystack-opensearch

An OpenSearch backend for [django-haystack](https://haystacksearch.org/).

**Documentation**: <https://django-haystack-opensearch.readthedocs.io>

`django-haystack-opensearch` provides a drop-in replacement for Elasticsearch
backends, allowing you to use OpenSearch (versions 1.x through 3.x) as your
search engine with
[django-haystack](https://https://github.com/django-haystack/django-haystack/).
It uses the `opensearch-py` client library only, instead of the out-of-date
`elasticsearch` client library.

## Core Features

- **Full-Text Search with OpenSearch**: Powerful full-text search capabilities with support for complex queries and relevance scoring.
- **Faceting and Filtering**: Support for field, date, and query facets. Efficient filtering on facet fields (requires `__exact` suffix).
- **Spatial/Geo Search**: Geographic location search, distance-based queries, and bounding box searches.
- **More Like This**: Similarity search to find related documents.
- **Highlighting and Spelling Suggestions**: Highlight search terms in results and provide automatic spelling correction.
- **Complete Haystack Compatibility**: Supports all standard Haystack features including field boosting, stored fields, and multiple connections.

## Requirements

- Python 3.11 or later
- Django 5.2 or later
- OpenSearch 1.x through 3.x
- django-haystack 3.3.0 or later

## Quick Start

### 1. Installation

Install the package using `pip`:

```bash
pip install django_haystack_opensearch
```

Or using `uv`:

```bash
uv add django_haystack_opensearch
```

### 2. Configuration

Add `haystack` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "haystack",
]
```

Configure the Haystack connection:

```python
HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
        "URL": "http://localhost:9200",
        "INDEX_NAME": "haystack",
    },
}
```

### 3. Usage

Define your search indexes as usual. When filtering on facet fields, remember to use the `__exact` suffix:

```python
from haystack.query import SearchQuerySet

# Filter by a facet field (requires __exact)
results = SearchQuerySet().filter(author__exact="John Doe")
```

## Common Use Cases

- **Adding Search to Django Applications**: Quickly add powerful search functionality to any Django project.
- **Migrating from Elasticsearch to OpenSearch**: A drop-in replacement for existing Elasticsearch backends with no code changes required.
- **Building Faceted Search Interfaces**: Create complex filter interfaces with accurate facet counts.

## Getting Help

- Check the [Documentation](https://django-haystack-opensearch.readthedocs.io) for detailed guides and examples.
- Report bugs or request features on the [GitHub Issues](https://github.com/caltechads/django-haystack-opensearch/issues) page.
- Explore the `sandbox/` directory for a complete demonstration application.
