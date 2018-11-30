.. highlight:: eql

=========================================
{{ source.name }}
=========================================
This is the mapping from {{ source.name }} native fields to the :doc:`{{ source.domain }} schema <../schemas>`.

Timestamp
---------

:field: ``{{source.timestamp.field}}``
:format: ``{{source.timestamp.format}}``

Globally provided mapping
-------------------------
{% for field, eql_text in source.fields.mapping.items() | sort %}
:{{field}}: ``{{eql_text}}``
{% endfor %}


Event specific mappings
-----------------------

{% for name, event_info in source.events.items() | sort %}
{{name}}
^^^^^^^^^^^^^^^^^^^^^^
``{{event_info.filter}}``

{% if event_info.enum %}
{% for enum_name, options_dict in event_info.enum.items() %}
**{{enum_name}}** mapping

{% for k, v in options_dict.items() | sort %}
:{{k}}: ``{{v}}``
{% endfor %}

{% endfor %}
{% endif %}

{% if event_info.mapping %}
**fields**

{% for field, eql_text in event_info.mapping.items() | sort %}
:{{field}}: ``{{eql_text}}``
{% endfor %}
{% endif %}

{% endfor %}
