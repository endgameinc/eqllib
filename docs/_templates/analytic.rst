.. include:: ../links.rst

========================================================
{{analytic.name}}
========================================================

{{analytic.metadata.description}}

:id: {{analytic.id}}
:categories: {{ analytic.metadata.categories | join(", ")}}
:confidence: {{analytic.metadata.confidence}}
:os: {{ analytic.metadata.os | join(", ")}}
:created: {{ analytic.metadata.created_date }}
:updated: {{ analytic.metadata.updated_date }}


MITRE ATT&CK™ Mapping
---------------------

:tactics: {% for tactic in analytic.metadata.tactics %}`{{tactic}}`_{{ ", " if not loop.last }}{% endfor %}
:techniques: {% for tech_id in analytic.metadata.techniques %}`{{tech_id}}`_ {{techniques[tech_id]['name']}}{{ ", " if not loop.last }}{% endfor %}

{% if analytic.metadata.notes %}
.. note::
    {{ analytic.metadata.notes.splitlines() | join("\n    ")}}
{% endif %}

Query
-----
.. code-block:: eql

    {{(analytic.metadata._source.splitlines()) | join("\n    ")}}

{% if "atomicblue" in analytic.metadata.get("tags", []) %}
Detonation
----------
`Atomic Red Team: {{analytic.metadata['techniques'][0]}} <https://github.com/redcanaryco/atomic-red-team/blob/master/atomics/{{analytic.metadata['techniques'][0]}}/{{analytic.metadata['techniques'][0]}}.md>`_
{% endif %}

Contributors
------------
{% for contributor in analytic.metadata.contributors %}
- `{{contributor}}`_
{% endfor %}


{% if analytic.metadata.references%}
References
----------
{% for ref in analytic.metadata.references %}
- {{ ref }}
{% endfor %}
{% endif %}
