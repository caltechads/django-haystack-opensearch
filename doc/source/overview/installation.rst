Installation
============

This guide covers how to install the ``django_haystack_opensearch`` package and its dependencies.

Prerequisites
-------------

Before installing ``django_haystack_opensearch``, ensure you have:

- Python 3.11 or higher
- `uv <https://docs.astral.sh/uv/>`_, `pip <https://pip.pypa.io/en/stable/>`_, or `pipx <https://pipx.pypa.io/stable/>`_

Installation Methods
--------------------

From PyPI with ``pip``
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    pip install django_haystack_opensearch


From PyPI with ``uv``
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    sh -c "$(curl -fsSL https://astral.sh/uv/install)"
    uv add django_haystack_opensearch

From PyPI with ``pipx``
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    pipx install django_haystack_opensearch


From Source
^^^^^^^^^^^

If you want to install from the latest development version:

.. code-block:: bash

    git clone https://github.com/caltechads/django_haystack_opensearch.git
    sh -c "$(curl -fsSL https://astral.sh/uv/install)"
    cd django_haystack_opensearch
    uv add file://../django_haystack_opensearch

.. _opensearch-plugins:

OpenSearch Plugins
------------------

Some advanced features of ``django_haystack_opensearch`` require specific plugins to
be installed on your OpenSearch node.

Ingest Attachment Plugin
^^^^^^^^^^^^^^^^^^^^^^^^

The :ref:`file-content-extraction` feature (``backend.extract_file_contents()``)
requires the ``ingest-attachment`` OpenSearch plugin.

**Installing via docker-compose**

If you are using Docker, you can automate the installation of this plugin in your
``docker-compose.yml`` by overriding the container command:

.. code-block:: yaml

    services:
      opensearch:
        image: opensearchproject/opensearch:1
        command: >
          /bin/bash -c "
            if ! bin/opensearch-plugin list | grep -q ingest-attachment; then
              bin/opensearch-plugin install --batch ingest-attachment
            fi
            /usr/share/opensearch/opensearch-docker-entrypoint.sh
          "
        # ... rest of your configuration ...

**Manual Installation**

You can also install it manually using the ``opensearch-plugin`` utility:

.. code-block:: bash

    bin/opensearch-plugin install ingest-attachment

**AWS OpenSearch Service**

If you are using AWS OpenSearch Service, you must associate the plugin with your
domain using the **Packages** feature:

1. Associate the plugin to your domain via the AWS Management Console, AWS CLI, or
   SDKs using the Packages feature.
2. Go to the **Packages** section in the OpenSearch Service console.
3. Locate the ``ingest-attachment`` package that matches your OpenSearch engine version.
4. Associate it with your domain. AWS will deploy the plugin and restart the domain
   nodes if needed.
5. Verify the installation by calling the plugin list API on your cluster:

   .. code-block:: http

       GET _cat/plugins?v

   You should see ``ingest-attachment`` in the list once successfully installed.

Configuration
-------------

After installation, you should to configure the library for your specific
environment.  See :doc:`configuration` for detailed configuration options.

Getting Help
------------

If you encounter issues during installation:

1. Check the `GitHub issues <https://github.com/caltechads/django_haystack_opensearch/issues>`_
2. Review the troubleshooting section above
3. Ensure your Python environment meets the prerequisites
4. Try installing in a virtual environment to isolate dependencies