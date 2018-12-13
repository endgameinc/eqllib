=======================
Schemas
=======================
.. toctree::
   :maxdepth: 0
   :hidden:

   schemas/sysmon
   schemas/car


Security Events
---------------
This is the primary schema used for normalizing across data sources.
Queries are written to match this schema, and data sources are converted to this schema.
This unifies sources to a unified by a common language and a common data model, so analytics can be written
generically and are easy shareable.

**Globally provided fields**


{% for field in domains['security']['fields'] | sort %}
- {{field}}
{% endfor %}

{% for name, event_info in domains['security']['events'].items() | sort%}
{{ name}}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

{% if event_info['enum'] %}
{% for field, values in event_info['enum'].items() | sort %}
**{{field}}** options

{% for value in values %}
- {{ value}}
{% endfor %}
{% endfor %}
{% endif %}

{% if event_info['fields'] %}
**fields**

{% for field in event_info['fields'] | sort %}
- {{field}}
{% endfor %}
{% endif %}

{% endfor %}