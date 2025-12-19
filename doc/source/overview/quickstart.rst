Quickstart Guide
================

This guide will get you up and running with ``django_haystack_opensearch`` quickly.

Prerequisites
-------------

- Python 3.11 or higher
- Django 5.2 or higher
- An OpenSearch server (1.x through 3.x)
- Follow the :doc:`/overview/installation` instructions to install ``django_haystack_opensearch``

Installation
------------

Install the package:

.. code-block:: bash

    pip install django_haystack_opensearch

Or using ``uv``:

.. code-block:: bash

    uv add django_haystack_opensearch

Configuration
-------------

Add ``haystack`` to your ``INSTALLED_APPS`` in ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = [
        # ... other apps
        "haystack",
    ]

Configure the Haystack connection:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": "http://localhost:9200",
            "INDEX_NAME": "haystack",
        },
    }

See :doc:`/overview/configuration` for more detailed configuration options.

Creating Search Indexes
-----------------------

Create a ``search_indexes.py`` file in your app directory:

.. code-block:: python

    from haystack import indexes
    from myapp.models import Article

    class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        title = indexes.CharField(model_attr="title")
        author = indexes.CharField(model_attr="author__name", faceted=True)
        created = indexes.DateTimeField(model_attr="created")

        def get_model(self):
            return Article

        def index_queryset(self, using=None):
            return self.get_model().objects.all()

Create a template for the text field at
``templates/search/indexes/myapp/article_text.txt``:

.. code-block:: text

    {{ object.title }}
    {{ object.content }}
    {{ object.author.name }}

Indexing Your Data
------------------

Build the search index:

.. code-block:: bash

    python manage.py rebuild_index

This will index all objects from your models that have search indexes defined.

Basic Search
------------

Perform a simple search:

.. code-block:: python

    from haystack.query import SearchQuerySet

    # Simple search
    results = SearchQuerySet().filter(content="django")

    for result in results:
        print(result.object.title)
        print(result.score)

Filter by facet fields (remember to use ``__exact``):

.. code-block:: python

    # Filter by author (facet field)
    results = SearchQuerySet().filter(author__exact="John Doe")

    # Combine with content search
    results = SearchQuerySet().filter(
        content="django",
        author__exact="John Doe"
    )

Add Faceting
------------

Get facet counts for building filter interfaces:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content="django").facet("author")
    results = list(sqs)

    # Get facet counts
    facets = sqs.facet_counts()
    author_facets = facets["fields"]["author"]

    for author, count in author_facets:
        print(f"{author}: {count}")

Next Steps
----------

Now that you have the basics working:

1. **Usage**: See :doc:`/overview/usage` for more advanced features and detailed examples.
2. **Configuration**: See :doc:`/overview/configuration` for configuration options.
3. **Demo**: Check out the :doc:`/overview/demo` guide to see a working example.
4. **FAQ**: See :doc:`/overview/faq` for common questions and troubleshooting.

Getting Help
------------

- Check the full documentation for detailed examples
- Review the :doc:`/overview/faq` section for common issues
- Report issues on the `GitHub repository <https://github.com/caltechads/django_haystack_opensearch/issues>`_
