Using django_haystack_opensearch
================================

This guide covers how to use ``django_haystack_opensearch`` to add powerful search
functionality to your Django applications using OpenSearch.

Basic Search
------------

The most basic search operation is to query the index for documents matching
a search term:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Simple text search
    results = SearchQuerySet().filter(content="django")

    # Auto-query (automatically parses the query string)
    results = SearchQuerySet().auto_query("django haystack")

    # Get all results
    all_results = SearchQuerySet().all()

    # Iterate over results
    for result in results:
        print(result.object)  # The Django model instance
        print(result.score)   # Relevance score

Filtering
---------

You can filter search results using various filter types:

Content Filtering
^^^^^^^^^^^^^^^^^

Filter on the main content field:

.. code-block:: python

    # Filter by content
    results = SearchQuerySet().filter(content="python")

Facet Field Filtering
^^^^^^^^^^^^^^^^^^^^^

**Important**: When filtering on facet fields, you must use the ``__exact`` suffix,
otherwise you will get no results.

This is because facet fields are automatically mapped to keyword fields in OpenSearch
for exact matching and aggregations. The backend creates a ``{field}_exact`` keyword
field for each facet field, and the ``__exact`` suffix tells Haystack to use this
exact field for filtering.

.. code-block:: python

    # Correct - for facet fields
    results = SearchQuerySet().filter(speaker_name__exact="KING HENRY")

    # Incorrect - will not work for facet fields
    # results = SearchQuerySet().filter(speaker_name="KING HENRY")  # This won't work!

    # Filter by multiple facet fields
    results = SearchQuerySet().filter(
        speaker_name__exact="KING HENRY",
        play_title__exact="Henry V"
    )

For non-facet fields, you can use standard filtering:

.. code-block:: python

    # For non-facet fields, standard filtering works
    results = SearchQuerySet().filter(content="king")

See :ref:`facet-field-filtering` for more details on why this is necessary.

Other Filter Types
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Contains (wildcard search)
    results = SearchQuerySet().filter(content__contains="django")

    # Starts with
    results = SearchQuerySet().filter(content__startswith="django")

    # Ends with
    results = SearchQuerySet().filter(content__endswith="search")

    # Exact match (for non-facet fields)
    results = SearchQuerySet().filter(content__exact="django haystack")

    # Greater than / Less than (for numeric/date fields)
    results = SearchQuerySet().filter(created__gte="2023-01-01")
    results = SearchQuerySet().filter(price__lt=100)

    # In (multiple values)
    results = SearchQuerySet().filter(id__in=[1, 2, 3])

    # Range
    results = SearchQuerySet().filter(price__range=[10, 50])

Faceting
--------

Faceting allows you to get counts of documents grouped by field values. This is
useful for building filter interfaces.

Field Facets
^^^^^^^^^^^^

Get counts for facet fields:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Add faceting to a query
    sqs = SearchQuerySet().facet("speaker_name").facet("play_title")

    # Execute the query
    results = list(sqs)

    # Get facet counts
    facets = sqs.facet_counts()

    # Access facet data
    speaker_facets = facets["fields"]["speaker_name"]
    # Returns: [("KING HENRY", 15), ("CHORUS", 8), ...]

    for value, count in speaker_facets:
        print(f"{value}: {count}")

Date Facets
^^^^^^^^^^^

Get counts grouped by date intervals:

.. code-block:: python

    from datetime import datetime, timedelta
    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().date_facet(
        "created",
        start_date=datetime.now() - timedelta(days=365),
        end_date=datetime.now(),
        gap_by="month",
        gap_amount=1
    )

    results = list(sqs)
    facets = sqs.facet_counts()

    date_facets = facets["dates"]["created"]
    # Returns: [(datetime(2023, 1, 1), 10), (datetime(2023, 2, 1), 15), ...]

Query Facets
^^^^^^^^^^^^

Get counts for custom query expressions:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().query_facet("recent", "created:[NOW-7DAYS TO NOW]")

    results = list(sqs)
    facets = sqs.facet_counts()

    recent_count = facets["queries"]["recent"]

Filtering by Facets
^^^^^^^^^^^^^^^^^^^

You can filter results using narrow queries based on facet values:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Use narrow() to filter by facet field values
    sqs = SearchQuerySet().narrow('speaker_name_exact:"KING HENRY"')

    # Combine with other filters
    sqs = SearchQuerySet().filter(content="king").narrow('play_title_exact:"Henry V"')

Highlighting
------------

Highlight search terms in results:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content="django").highlight()
    results = list(sqs)

    for result in results:
        if hasattr(result, "highlighted"):
            print(result.highlighted)  # HTML with <em> tags around matches

.. _spelling-suggestions:

Spelling Suggestions
--------------------

Get spelling suggestions for queries:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content="djangoo")  # Misspelled
    results = list(sqs)

    # Get spelling suggestion
    suggestion = sqs.spelling_suggestion()
    if suggestion:
        print(f"Did you mean: {suggestion}")

How it Works
^^^^^^^^^^^^

By default, the OpenSearch backend uses the main document field (the one with
``document=True``) to generate spelling suggestions.

For better results, you can provide a dedicated spelling field in your
``SearchIndex``. This is useful if you want to use a different analyzer for
spelling than for your main content (e.g., a non-stemmed analyzer).

To use a dedicated spelling field, simply name it ``_spelling``:

.. code-block:: python

    class MyIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        # Dedicated spelling field
        _spelling = indexes.CharField(model_attr='my_content_field')

The backend will automatically detect this field and use it for suggestions.

More Like This
--------------

Find documents similar to a given document:

.. code-block:: python

    from haystack.query import SearchQuerySet
    from myapp.models import Article

    # Get a document
    article = Article.objects.get(pk=1)

    # Find similar documents
    backend = connections["default"].get_backend()
    similar = backend.more_like_this(article)

    similar_results = similar["results"]
    for result in similar_results:
        print(result.object)

You can also add additional query constraints:

.. code-block:: python

    similar = backend.more_like_this(
        article,
        additional_query_string="category:technology"
    )

Spatial Search
--------------

Search by geographic location:

Within a Bounding Box
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point

    # Define bounding box corners
    point1 = Point(-122.5, 37.7)  # Southwest corner
    point2 = Point(-122.3, 37.9)  # Northeast corner

    # Search within bounding box
    sqs = SearchQuerySet().within("location", point1, point2)

Within a Distance
^^^^^^^^^^^^^^^^^

.. code-block:: python

    from haystack.query import SearchQuerySet
    from django.contrib.gis.geos import Point
    from django.contrib.gis.measure import D

    # Define center point
    center = Point(-122.4, 37.8)

    # Search within 10km
    sqs = SearchQuerySet().dwithin("location", center, D(km=10))

    # Sort by distance
    sqs = sqs.distance("location", center).order_by("distance")

    for result in sqs:
        print(f"{result.object}: {result._distance}")

Sorting
-------

Sort results by field values:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Sort ascending
    sqs = SearchQuerySet().order_by("created")

    # Sort descending
    sqs = SearchQuerySet().order_by("-created")

    # Multiple sort fields
    sqs = SearchQuerySet().order_by("-score", "created")

Pagination
----------

Paginate search results:

.. code-block:: python

    from haystack.query import SearchQuerySet
    from django.core.paginator import Paginator

    sqs = SearchQuerySet().filter(content="django")

    # Using Django's paginator
    paginator = Paginator(sqs, 20)  # 20 results per page
    page = paginator.page(1)

    for result in page:
        print(result.object)

    # Or use slicing
    page1 = sqs[0:20]
    page2 = sqs[20:40]

Model Filtering
---------------

Filter results to specific Django models:

.. code-block:: python

    from haystack.query import SearchQuerySet
    from myapp.models import Article, BlogPost

    # Filter to specific models
    sqs = SearchQuerySet().models(Article)

    # Multiple models
    sqs = SearchQuerySet().models(Article, BlogPost)

Stored Fields
-------------

Retrieve specific stored fields (non-indexed fields):

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Fields marked with indexed=False are stored but not searchable
    # They can be retrieved directly from search results
    sqs = SearchQuerySet().filter(content="django")

    for result in sqs:
        # Access stored fields directly
        stored_value = result.stored_field_name

Boost
-----

Boost certain fields or queries for relevance:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Fields can be boosted in the search index definition
    # Higher boost = more relevant

    # You can also boost in queries
    sqs = SearchQuerySet().boost("title", 2.0).filter(content="django")

Advanced Usage
--------------

Combining Features
^^^^^^^^^^^^^^^^^

You can combine multiple features in a single query:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = (
        SearchQuerySet()
        .models(Article)
        .filter(content="django")
        .facet("category")
        .facet("author")
        .highlight()
        .order_by("-score")
    )

    results = list(sqs)
    facets = sqs.facet_counts()

    # Process results
    for result in results:
        print(f"{result.object.title}: {result.score}")
        if hasattr(result, "highlighted"):
            print(f"  {result.highlighted}")

Using Multiple Connections
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you've configured multiple connections, you can use them:

.. code-block:: python

    from haystack import connections
    from haystack.query import SearchQuerySet

    # Use default connection
    sqs = SearchQuerySet()

    # Use specific connection
    sqs = SearchQuerySet(using="readonly")

Indexing
--------

Indexing Your Models
^^^^^^^^^^^^^^^^^^^^

After defining your search indexes (see :doc:`/overview/quickstart`), you need to
index your data:

.. code-block:: bash

    # Rebuild the entire index
    python manage.py rebuild_index

    # Update the index (incremental)
    python manage.py update_index

    # Clear the index
    python manage.py clear_index

Programmatic Indexing
^^^^^^^^^^^^^^^^^^^^^

You can also index programmatically:

.. code-block:: python

    from haystack import connections
    from myapp.models import Article
    from myapp.search_indexes import ArticleIndex

    backend = connections["default"].get_backend()
    index = ArticleIndex()

    # Index a single object
    backend.update(index, [article])

    # Index multiple objects
    articles = Article.objects.all()
    backend.update(index, articles)

    # Remove from index
    backend.remove(article)

.. _facet-field-filtering:

Understanding Facet Field Filtering
------------------------------------

Why ``__exact`` is Required for Facet Fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you define a field as ``faceted=True`` in your search index, the backend
automatically creates two field mappings in OpenSearch:

1. The original field (for full-text search if it's a text field)
2. A ``{field}_exact`` keyword field (for exact matching and aggregations)

For example, if you have:

.. code-block:: python

    class SpeechIndex(indexes.SearchIndex, indexes.Indexable):
        speaker_name = indexes.CharField(model_attr="speaker__name", faceted=True)

The backend creates:
- ``speaker_name`` - the original field
- ``speaker_name_exact`` - a keyword field for exact matching

When you use ``filter(speaker_name__exact="KING HENRY")``, Haystack translates
this to query the ``speaker_name_exact`` keyword field, which provides exact
matching suitable for filtering.

If you use ``filter(speaker_name="KING HENRY")`` without ``__exact``, Haystack
tries to query the ``speaker_name`` field, which may be a text field that
undergoes analysis (tokenization, lowercasing, etc.), making exact matches
unreliable or impossible.

This is why facet fields require the ``__exact`` suffix for filtering. The
backend's ``get_facet_fieldname()`` method automatically returns the ``_exact``
suffix for facet fields to ensure correct filtering behavior.

For a working example, see the test in ``sandbox/demo/core/tests.py`` in the
``TestQueryFilters.test_filter_exact`` method.
