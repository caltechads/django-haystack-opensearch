Configuration
=============

This guide covers all configuration options for the
``django_haystack_opensearch`` Django library, including
Django settings and environment variables.

``django_haystack_opensearch`` is a __FILL_ME_IN__.  The default
configuration should work for most use cases, but you can customise behavior
through various configuration methods.

INSTALLED_APPS
--------------

To configure this library in your project, it must be added to the
``INSTALLED_APPS`` list in your project's ``settings.py`` file.

Example:

.. code-block:: python

    INSTALLED_APPS = [
        ...,
        "django_haystack_opensearch",
        ...,
    ]

Django Settings
---------------

All settings for this app should be defined in a dictionary called ``DJANGO_HAYSTACK_OPENSEARCH_SETTINGS`` in your project's settings.py file.
The dictionary should be empty by default, and you can add settings to it as needed.

Example:

.. code-block:: python

    DJANGO_HAYSTACK_OPENSEARCH_SETTINGS = {
        "SETTING_NAME": "SETTING_VALUE",
    }

We ship the app with the following default settings, as keys in the dictionary.

- ``SETTING_1``: The first setting, populated via the :envvar:`DJANGO_HAYSTACK_OPENSEARCH_SETTING_1` environment variable.
- ``SETTING_2``: The second setting, populated via the :envvar:`DJANGO_HAYSTACK_OPENSEARCH_SETTING_2` environment variable.
- ``SETTING_3``: The third setting, populated via the :envvar:`DJANGO_HAYSTACK_OPENSEARCH_SETTING_3` environment variable.

Best Practices
--------------

Configuration Management
^^^^^^^^^^^^^^^^^^^^^^^^^

1. **Use Django settings for defaults**

   - Set common settings in ``your_project/settings.py``
   - Use environment variables for overrides
   - Use command-line options for one-time changes

2. **Separate environments**

   - Use environment variables to configure settingsfor different environments
   - Document required environment variables

3. **Version control**

   - Don't commit sensitive configuration
   - Document required settings

4. **Security**

   - Use environment variables for credentials
   - Protect environment variables with proper permissions (e.g. .env file)

5. **Testing**

   - Test timeout settings for your environment
   - Verify output formats work for your use case
   - Test logging configuration