# django-haystack-opensearch

An OpenSearch backend for [django-haystack](https://haystacksearch.org/).

**Documentation**: [django_haystack_opensearch.readthedocs.org](https://django_haystack_opensearch.readthedocs.org)

`django-haystack-opensearch` provides a pure `opensearch-py` based backend for `django-haystack`, allowing you to use OpenSearch (versions 1.x through 3.x) as your search engine without requiring the legacy `elasticsearch-py` client.

## Core Features

- **Full-Text Search with OpenSearch**: Powerful full-text search capabilities with support for complex queries and relevance scoring.
- **Faceting and Filtering**: Support for field, date, and query facets. Efficient filtering on facet fields (requires `__exact` suffix).
- **Spatial/Geo Search**: Geographic location search, distance-based queries, and bounding box searches.
- **More Like This**: Similarity search to find related documents based on content.
- **Highlighting and Spelling Suggestions**: Highlight search terms in results and provide automatic spelling correction.
- **File Content Extraction**: Extract text and metadata from binary files (PDF, DOCX, etc.) using OpenSearch's `ingest-attachment` plugin.
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

### 3. Creating Search Indexes

Create a `search_indexes.py` file in your app directory:

```python
from haystack import indexes
from myapp.models import Article

class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    author = indexes.CharField(model_attr="author__name", faceted=True)

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
```

### 4. Indexing Your Data

Build the search index:

```bash
python manage.py rebuild_index
```

### 5. Basic Usage

Perform a simple search:

```python
from haystack.query import SearchQuerySet

# Simple text search
results = SearchQuerySet().filter(content="django")

# Filter by a facet field (requires __exact)
results = SearchQuerySet().filter(author__exact="John Doe")
```

## Common Use Cases

- **Adding Search to Django Applications**: Quickly add powerful search functionality to any Django project.
- **Migrating from Elasticsearch to OpenSearch**: A drop-in replacement for existing Elasticsearch backends with minimal code changes.
- **Building Faceted Search Interfaces**: Create complex filter interfaces with accurate facet counts.
- **Advanced Features**: Implement spatial search, "More Like This" recommendations, and file content extraction.

## Getting Help

- Check the [Full Documentation](https://django_haystack_opensearch.readthedocs.org) for detailed guides and examples.
- Report bugs or request features on the [GitHub Issues](https://github.com/caltechads/django-haystack-opensearch/issues) page.
- Explore the `sandbox/` directory for a complete demonstration application.
