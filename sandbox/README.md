# django-haystack-opensearch Sandbox

This is a demonstration Django application for the `django_haystack_opensearch`
module. It indexes and searches through Shakespeare plays, demonstrating
features like faceting, filtering, and highlighting.

## Documentation

Full documentation for this project is available on [ReadTheDocs](https://django-haystack-opensearch.readthedocs.io).

## Running the Demo

The demo runs entirely in Docker, so you will need Docker Desktop or equivalent
installed on your development machine.

### 1. Build the Docker image

From the `sandbox/` directory, run:

```bash
make build
```

This will package the library, install all dependencies, and prepare the demo application.

### 2. Start the services

Start the Django application, MySQL database, and OpenSearch server in the background:

```bash
make dev-detached
```

### 3. Automatic Initialization

When the container starts, it will automatically:

- Run database migrations (which includes loading the Shakespeare play data)
- Create the search index in OpenSearch
- Index all documents

You can follow the progress by checking the logs:

```bash
make logall
```

### 4. Access the application

Once the services are healthy, you can browse to the demo app at:

- **Web Interface**: <https://localhost/>
- **OpenSearch**: <http://localhost:9200>

## Management Commands

The demo container includes several management commands for exploring the module:

- `./manage.py import_play`: Import a play from a text file.
- `./manage.py rebuild_index`: Clear and rebuild the search index.
- `./manage.py update_index`: Update the index with new/modified data.

To run commands inside the container:

```bash
make exec
./manage.py <command>
```
