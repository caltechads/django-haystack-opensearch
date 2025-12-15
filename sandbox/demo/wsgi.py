import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# This allows easy placement of apps within the interior demo directory.
app_path = Path(__file__).parent.parent
sys.path.append(str(app_path / "demo"))

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo.settings")

# This application object is used by any WSGI server configured to use this file.
application = get_wsgi_application()
