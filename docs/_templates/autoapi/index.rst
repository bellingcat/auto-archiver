API Reference
=============

These pages are intended for developers of the `auto-archiver` package, 
and include documentation on the core classes and functions used by 
the auto-archiver


Core Classes
------------


.. toctree::
   :titlesonly:

   {% for page in pages|selectattr("is_top_level_object") %}
   {% if page.name == 'core' %}
   {{ page.include_path }}
   {% endif %}
   {% endfor %}

Util Functions
--------------

.. toctree::
   :titlesonly:

   {% for page in pages|selectattr("is_top_level_object") %}
   {% if page.name == 'utils' %}
   {{ page.include_path }}
   {% endif %}
   {% endfor %}


Core Modules
------------

.. toctree::
   :titlesonly:

   {% for page in pages|selectattr("is_top_level_object") %}
   {% if page.name != 'core' and page.name != 'utils' %}
   {{ page.include_path }}
   {% endif %}
   {% endfor %}

