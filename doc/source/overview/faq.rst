Frequently Asked Questions
==========================

This section answers common questions about django_haystack_opensearch and provides
solutions to frequently encountered issues.

General Questions
------------------

What is django_haystack_opensearch?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``django_haystack_opensearch`` is an OpenSearch backend for django-haystack. It
provides a drop-in replacement for Elasticsearch backends, allowing you to use
OpenSearch (versions 1.x through 3.x) as your search engine with django-haystack.

Key features:

- Full compatibility with django-haystack's API
- Support for all Haystack features (faceting, highlighting, More Like This, etc.)
- Compatible with OpenSearch 1.x through 3.x
- Uses the opensearch-py client library
- API compatibility with elasticsearch7_backend

What versions of OpenSearch are supported?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``django_haystack_opensearch`` supports **OpenSearch 1.x through 3.x**. The backend
uses the `opensearch-py>=3.1.0` client library, which provides compatibility
across these versions.

Installation Issues
-------------------

How do I install django_haystack_opensearch?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

See the :doc:`/overview/installation` guide for detailed installation instructions.
The recommended methods are:

- Using ``pip``: ``pip install django_haystack_opensearch``
- Using ``uv``: ``uv add django_haystack_opensearch``
- From source: Clone the repository and install with ``pip install -e .``

Then see the :doc:`/overview/configuration` guide for how to configure the library
in your project.

Usage Questions
---------------

Why do facet fields require ``__exact`` when filtering?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you define a field as ``faceted=True`` in your search index, the backend
automatically creates a ``{field}_exact`` keyword field in OpenSearch for exact
matching and aggregations. This is necessary because:

1. Facet fields need to be stored as keywords (not analyzed text) for accurate
   counting and exact matching
2. The original field may be analyzed (tokenized, lowercased, etc.), making exact
   matches unreliable

When you use ``filter(speaker_name__exact="KING HENRY")``, Haystack queries the
``speaker_name_exact`` keyword field, which provides exact matching.

If you use ``filter(speaker_name="KING HENRY")`` without ``__exact``, Haystack
tries to query the analyzed ``speaker_name`` field, which may not match exactly.

For more details, see the :doc:`/overview/usage` guide section on
:ref:`facet-field-filtering`.

How do I search across multiple models?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``models()`` method to search across specific models:

.. code-block:: python

    from haystack.query import SearchQuerySet
    from myapp.models import Article, BlogPost

    # Search across multiple models
    results = SearchQuerySet().models(Article, BlogPost).filter(content="django")

How do I get facet counts?
^^^^^^^^^^^^^^^^^^^^^^^^^^

Add faceting to your query and then call ``facet_counts()``:

.. code-block:: python

    from haystack.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content="django").facet("author")
    results = list(sqs)
    facets = sqs.facet_counts()

    author_facets = facets["fields"]["author"]

See the :doc:`/overview/usage` guide for more examples.

Troubleshooting
---------------

I'm getting no results when filtering on facet fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure you're using the ``__exact`` suffix when filtering on facet fields:

.. code-block:: python

    # Correct
    results = SearchQuerySet().filter(author__exact="John Doe")

    # Incorrect - will return no results
    # results = SearchQuerySet().filter(author="John Doe")

See :ref:`facet-field-filtering` in the usage guide for an explanation.

Connection errors to OpenSearch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you're getting connection errors:

1. **Check the URL**: Make sure the ``URL`` setting points to your OpenSearch
   server (e.g., ``http://localhost:9200``)

2. **Check authentication**: If your OpenSearch server requires authentication,
   make sure you've configured it in the ``KWARGS`` setting:

   .. code-block:: python

       HAYSTACK_CONNECTIONS = {
           "default": {
               "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
               "URL": "http://opensearch.example.com:9200",
               "INDEX_NAME": "haystack",
               "KWARGS": {
                   "http_auth": ("username", "password"),
               },
           },
       }

3. **Check SSL settings**: If using HTTPS, configure SSL properly:

   .. code-block:: python

       "KWARGS": {
           "use_ssl": True,
           "verify_certs": True,
           "ca_certs": "/path/to/ca-certificates.crt",
       }

4. **Check network connectivity**: Ensure your Django application can reach
   the OpenSearch server

Index not found errors
^^^^^^^^^^^^^^^^^^^^^^

If you get index not found errors:

1. **Create the index**: Run ``python manage.py rebuild_index`` to create and
   populate the index

2. **Check INDEX_NAME**: Make sure the ``INDEX_NAME`` setting matches what you
   expect

3. **Check permissions**: Ensure your OpenSearch user has permissions to create
   and write to indices

Performance and Limitations
----------------------------

What are the performance characteristics?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Performance depends on several factors:

- **Index size**: Larger indices take longer to search
- **Query complexity**: Complex queries with many filters and facets are slower
- **Network latency**: Distance to OpenSearch server affects response time
- **OpenSearch configuration**: Hardware, sharding, and replication settings

For best performance:

- Use appropriate index settings (shards, replicas)
- Limit the number of facets in a single query
- Use pagination to limit result sets
- Consider caching frequently-used queries

Are there any limitations?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The backend is designed for OpenSearch 1.x through 3.x. Other versions may
  work but are not officially supported
- Some advanced OpenSearch features may not be directly accessible through
  the Haystack API
- Very large result sets may require special handling (use pagination)

Migration from Elasticsearch
-----------------------------

Can I migrate from an Elasticsearch backend?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Yes! ``django_haystack_opensearch`` is designed as a drop-in replacement for
Elasticsearch backends. The API is compatible with ``elasticsearch7_backend``.

To migrate:

1. Install ``django_haystack_opensearch``
2. Update your ``HAYSTACK_CONNECTIONS`` setting to use the OpenSearch engine
3. Update the ``URL`` to point to your OpenSearch server
4. Rebuild your index: ``python manage.py rebuild_index``

Your search indexes and queries should work without modification.

Getting Help
------------

Where can I get more help?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Documentation**: Check the other sections of this documentation:
   - :doc:`/overview/installation` - Installation guide
   - :doc:`/overview/quickstart` - Quick start guide
   - :doc:`/overview/usage` - Detailed usage guide
   - :doc:`/overview/configuration` - Configuration options

2. **GitHub issues**: Report bugs or request features on the
   `project repository <https://github.com/caltechads/django_haystack_opensearch/issues>`_

3. **Demo application**: Check out the :doc:`/overview/demo` guide to see a
   working example

How do I report a bug?
^^^^^^^^^^^^^^^^^^^^^^

When reporting a bug, please include:

1. **Error message**: The complete error output, including the traceback
2. **Environment**:
   - OS and version
   - Python version
   - Django version
   - django_haystack_opensearch version
   - OpenSearch version
3. **Steps to reproduce**: The exact steps to reproduce the bug
4. **Configuration**: Relevant parts of your ``HAYSTACK_CONNECTIONS`` setting
   (redact any sensitive information)

Example bug report:

.. code-block:: text

    Error: ConnectionError when querying OpenSearch

    Traceback:
    [Include traceback here]

    Environment:
    - OS: Ubuntu 22.04
    - Python: 3.11
    - Django: 5.2
    - django_haystack_opensearch: 0.1.0
    - OpenSearch: 2.11.0

    Steps to reproduce:
    1. Configure connection to OpenSearch server
    2. Run: python manage.py rebuild_index
    3. Error occurs
