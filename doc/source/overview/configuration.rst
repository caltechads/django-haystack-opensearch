Configuration
=============

This guide covers all configuration options for the
``django_haystack_opensearch`` Django library, including Django Haystack settings and
environment variables.

``django_haystack_opensearch`` is a Django Haystack backend for OpenSearch.  The default
configuration should work for most use cases, but you can customise behavior
through various configuration methods.

OpenSearch Version Support
--------------------------

``django_haystack_opensearch`` is compatible with **OpenSearch 1.x through 3.x**. It uses
the `opensearch-py>=3.1.0` client library and maintains API compatibility with
the elasticsearch7_backend, making it a drop-in replacement for Elasticsearch
backends in django-haystack.

Django Haystack Settings
------------------------

To configure the Haystack backend, you can set the ``HAYSTACK_CONNECTIONS`` setting in your project's ``settings.py`` file.

Required Settings
^^^^^^^^^^^^^^^^^

The following settings are required:

- **ENGINE**: Must be set to ``django_haystack_opensearch.haystack.OpenSearchSearchEngine``
- **URL**: The URL of your OpenSearch server (e.g., ``http://localhost:9200``)
- **INDEX_NAME**: The name of the index to use for search

Example:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": os.getenv("OPENSEARCH_URL", "http://localhost:9200"),
            "INDEX_NAME": os.getenv("OPENSEARCH_INDEX_NAME", "haystack"),
        },
    }

Optional Settings
^^^^^^^^^^^^^^^^^

- **TIMEOUT**: Request timeout in seconds (default: 10)
- **KWARGS**: Additional keyword arguments passed to the OpenSearch client constructor

Common configuration options in ``KWARGS``:

- **http_auth**: Tuple of (username, password) for HTTP basic authentication
- **use_ssl**: Boolean to enable SSL/TLS
- **verify_certs**: Boolean to verify SSL certificates
- **ssl_show_warn**: Boolean to show SSL warnings
- **ca_certs**: Path to CA certificates file
- **client_cert**: Path to client certificate file
- **client_key**: Path to client key file

Example with authentication:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": os.getenv("OPENSEARCH_URL"),
            "INDEX_NAME": os.getenv("OPENSEARCH_INDEX_NAME"),
            "TIMEOUT": 60 * 5,  # 5 minutes
            "KWARGS": {
                "http_auth": (os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD")),
            },
        },
    }

Example with SSL:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": "https://opensearch.example.com:9200",
            "INDEX_NAME": "haystack",
            "KWARGS": {
                "use_ssl": True,
                "verify_certs": True,
                "ca_certs": "/path/to/ca-certificates.crt",
            },
        },
    }

Example with API key authentication:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": os.getenv("OPENSEARCH_URL"),
            "INDEX_NAME": os.getenv("OPENSEARCH_INDEX_NAME"),
            "KWARGS": {
                "headers": {
                    "Authorization": f"ApiKey {os.getenv('OPENSEARCH_API_KEY')}",
                },
            },
        },
    }

Multiple Connections
^^^^^^^^^^^^^^^^^^^^

You can configure multiple OpenSearch connections for different purposes:

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": "http://localhost:9200",
            "INDEX_NAME": "haystack",
        },
        "readonly": {
            "ENGINE": "django_haystack_opensearch.haystack.OpenSearchSearchEngine",
            "URL": "http://readonly-opensearch:9200",
            "INDEX_NAME": "haystack",
        },
    }

Best Practices
--------------

Configuration Management
^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Use Django settings for defaults**

   - Set common settings in ``your_project/settings.py``
   - Use environment variables for overrides
   - Use different connection aliases for different environments

2. **Separate environments**

   - Use environment variables to configure settings for different environments
   - Document required environment variables
   - Use different index names for development, staging, and production

3. **Version control**

   - Don't commit sensitive configuration (passwords, API keys)
   - Document required settings in your project's README
   - Use example configuration files (e.g., ``settings.example.py``)

4. **Security**

   - Use environment variables for credentials
   - Protect environment variables with proper permissions (e.g., .env file)
   - Use SSL/TLS in production environments
   - Rotate credentials regularly

5. **Testing**

   - Test timeout settings for your environment
   - Use separate indices for testing
   - Verify connection settings work before deploying
