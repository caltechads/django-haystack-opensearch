Demo Application
================

The ``django_haystack_opensearch`` project includes a demo application in the
``sandbox/`` directory that demonstrates the full capabilities of the backend.
The demo is a Django application that indexes and searches through Shakespeare
plays, showing features like faceting, filtering, and highlighting.

Prerequisites
-------------

To run the demo application, you need:

- **Docker Desktop** (or equivalent Docker environment)
- Docker Compose (usually included with Docker Desktop)

The demo runs entirely in Docker containers, so you don't need to install
OpenSearch or MySQL locally.

Setting Up the Demo
-------------------

1. **Navigate to the sandbox directory**:

   .. code-block:: bash

       cd sandbox

2. **Build the Docker image**:

   .. code-block:: bash

       make build

   This will:
   - Package the django_haystack_opensearch library
   - Build the Docker image with all dependencies
   - Set up the demo application

3. **Start the services**:

   .. code-block:: bash

       make dev-detached

   This starts:

   - The Django demo application
   - MySQL database
   - OpenSearch server

   Services will start in the background. You can check logs with:

   .. code-block:: bash

       make logall


    This will automatically run the database migrations, load the demo data, and
    build the search index.

The application will be available at `<https://localhost/>`_.


Accessing the Demo
------------------

Once the services are running, you can access the demo application at:

- **Web interface**: https://localhost/
- **OpenSearch**: http://localhost:9200
- **MySQL**: localhost:3306

The web interface provides a search interface where you can:

- Search for speeches by content
- Filter by speaker, act, scene, or play
- See facet counts for each filter
- View highlighted search results
- Explore the full-text search capabilities

Management Commands
-------------------

The demo includes several management commands:

import_play
^^^^^^^^^^^

Import a play from a text file:

.. code-block:: bash

    ./manage.py import_play <file_path> --title "Play Title"

Options:

- ``--title``: Title for the play (required)
- ``--output-fixture``: Generate a fixture file instead of saving to database
- ``--dry-run``: Parse the file without saving to database

Example:

.. code-block:: bash

    ./manage.py import_play data/henry-v.txt --title "Henry V"

rebuild_index
^^^^^^^^^^^^^

Rebuild the entire search index:

.. code-block:: bash

    ./manage.py rebuild_index

This will index all speeches, speakers, and plays.

update_index
^^^^^^^^^^^^

Update the index with any new or modified objects:

.. code-block:: bash

    ./manage.py update_index

clear_index
^^^^^^^^^^^

Clear all documents from the search index:

.. code-block:: bash

    ./manage.py clear_index

Useful Commands
---------------

View logs:

.. code-block:: bash

    # All services
    make logall

    # Just the Django app
    make log

Restart the Django application:

.. code-block:: bash

    make restart

Stop all services:

.. code-block:: bash

    make devdown

Open a shell in the container:

.. code-block:: bash

    make exec

Exploring the Demo
------------------

The demo application demonstrates:

1. **Basic Search**: Search speeches by content
2. **Faceting**: Get counts by speaker, act, scene, and play
3. **Filtering**: Filter results using facet fields (with ``__exact``)
4. **Highlighting**: See search terms highlighted in results
5. **Multi-value Facets**: Speakers appear in multiple plays
6. **Complex Queries**: Combine multiple filters and facets

The search indexes are defined in ``sandbox/demo/core/search_indexes.py``:

- ``SpeechIndex``: Indexes individual speeches with faceted fields for speaker,
  act, scene, and play
- ``SpeakerIndex``: Indexes speakers with multi-value facets for plays, acts,
  and scenes they appear in
- ``PlayIndex``: Indexes plays with template-based document fields

You can explore the code to see how these features are implemented.

Troubleshooting
---------------

Services won't start
^^^^^^^^^^^^^^^^^^^^

- Make sure Docker Desktop is running
- Check that ports 443, 9200, and 3306 are not in use
- Try ``make devdown`` then ``make dev-detached`` again

Can't connect to OpenSearch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Wait a few seconds after starting services - OpenSearch takes time to start
- Check logs: ``make logall``
- Verify OpenSearch is healthy: ``curl http://localhost:9200``

Database connection errors
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Make sure MySQL container is healthy (check ``make logall``)
- Wait for MySQL to fully initialize before running migrations
- The healthcheck should show MySQL is ready before Django starts

Index is empty
^^^^^^^^^^^^^^

- Make sure you've loaded data: ``./manage.py loaddata core/fixtures/henry_v.json``
- Rebuild the index: ``./manage.py rebuild_index``
- Check that data exists: ``./manage.py shell`` then ``from demo.core.models import Speech; print(Speech.objects.count())``

For more information, see the ``sandbox/README.md`` file.

