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