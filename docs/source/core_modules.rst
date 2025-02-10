Core Modules
============

These pages are intended for developers of the `auto-archiver` package, and include documentation on the core classes and functions used by the auto-archiver

.. toctree::
   :titlesonly:

   {% for page in pages|selectattr("is_top_level_object") %}
   {{ page.include_path }}
   {% endfor %}
