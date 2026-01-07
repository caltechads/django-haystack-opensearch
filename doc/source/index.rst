==========================
django_haystack_opensearch
==========================

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   overview/installation
   overview/quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide
   :hidden:

   overview/usage
   overview/configuration
   overview/faq
   overview/demo

.. toctree::
   :maxdepth: 2
   :caption: Development
   :hidden:

   runbook/contributing
   runbook/coding_standards

.. toctree::
   :maxdepth: 2
   :caption: Reference
   :hidden:

   changelog
   api/backend

Current version is |release|.

``django_haystack_opensearch`` is an OpenSearch backend for `django-haystack
<https://django-haystack.readthedocs.io/>`_. It provides a pure `opensearch-py
<https://opensearch-py.readthedocs.io/>`_ based backend, allowing you to use
OpenSearch (versions 1.x through 3.x) as your search engine with django-haystack
without elasticsearch-py.

The backend is fully compatible with django-haystack's API and supports all
standard Haystack features including faceting, highlighting, More Like This,
spatial search, and more.

Core Features
-------------

django_haystack_opensearch provides the following key features:

**Full-Text Search with OpenSearch**
    - Powerful full-text search capabilities
    - Support for complex queries and filters
    - Relevance scoring and ranking

**Faceting and Filtering**
    - Field facets for grouping and counting
    - Date facets for time-based analysis
    - Query facets for custom aggregations
    - Efficient filtering on facet fields

**Spatial/Geo Search**
    - Geographic location search
    - Distance-based queries
    - Bounding box searches

**More Like This**
    - Find similar documents
    - Content-based recommendations
    - Similarity scoring

**Highlighting and Spelling Suggestions**
    - Highlight search terms in results
    - Automatic spelling correction
    - Query suggestions

**Importing files (PDF, DOCX, etc.)**
    - Extract text and metadata from binary files
    - Use OpenSearch's ``ingest-attachment`` plugin to extract the contents of files
    - Supports all file types supported by the ``ingest-attachment`` plugin

**All Standard Haystack Features**
    - Complete API compatibility
    - Model filtering
    - Sorting and pagination
    - Stored fields
    - Field boosting
    - Index management
    - And more!

Getting Started
---------------

To get started with django_haystack_opensearch:

1. **Installation**: Follow the :doc:`/overview/installation` guide
2. **Quick Start**: See the :doc:`/overview/quickstart` guide for basic usage
3. **Usage Guide**: Learn about commands and options in :doc:`/overview/usage`
4. **Configuration**: Learn about configuration options in :doc:`/overview/configuration`
5. **Demo**: Check out the :doc:`/overview/demo` guide to see a working example
6. **FAQ**: Check the :doc:`/overview/faq` section for common questions and troubleshooting

For developers, see the :doc:`/runbook/contributing` and :doc:`/runbook/coding_standards` guides.

Requirements
------------

- Python 3.11 or later
- Django 5.2 or later
- OpenSearch 1.x through 3.x
- django-haystack 3.3.0 or later

Common Use Cases
----------------

**Adding Search to Django Applications**
    - Quickly add powerful search functionality to any Django project
    - Index and search across multiple models
    - Build faceted search interfaces

**Migrating from Elasticsearch to OpenSearch**
    - Drop-in replacement for Elasticsearch backends
    - No code changes required
    - Same API, different backend

**Building Faceted Search Interfaces**
    - Create filter interfaces with facet counts
    - Support for multiple facet types
    - Efficient filtering and aggregation

**Implementing Advanced Search Features**
    - More Like This recommendations
    - Geographic search
    - Highlighting and spelling correction
    - Complex query combinations

Getting Help
------------

If you need help with django_haystack_opensearch:

**Documentation**
    - Check the :doc:`/overview/faq` for common questions
    - Review the :doc:`/overview/usage` guide for detailed examples
    - See the :doc:`/overview/configuration` guide for setup options

**GitHub Issues**
    - Report bugs or request features on the
      `GitHub repository <https://github.com/caltechads/django_haystack_opensearch/issues>`_
    - Search existing issues before creating a new one
    - Include relevant details when reporting bugs

**Troubleshooting**
    - Check the :doc:`/overview/faq` troubleshooting section
    - Review error messages and tracebacks carefully
    - Verify your configuration matches the examples

**Demo Application**
    - Explore the :doc:`/overview/demo` to see a working example
    - Study the demo code for implementation patterns
    - Use the demo as a reference for your own projects

When reporting issues, please include:

- Your Python, Django, and OpenSearch versions
- Relevant configuration (redact sensitive information)
- Error messages and tracebacks
- Steps to reproduce the issue
