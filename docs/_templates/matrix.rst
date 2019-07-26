.. include:: ../links.rst

========================
{{platform}}
========================


.. list-table::
    :header-rows: 1
    :class: attack-matrix

    * {% for tactic in tactics %}- `{{tactic.name}}`_
      {% endfor %}

    {% for row in matrix_cells %}
    * {% for tactic, technique in zip(tactics, row) %}- {% if technique %}`{{technique.name}}`_
        {% for analytic in coverage[tactic.name][technique.external_references[0].external_id] %}
        {% if not os or platform.lower() in analytic.metadata.os %}- :doc:`../analytics/{{analytic.id}}`{% if show_os %} ({{analytic.metadata.os | sort|join(", ", 0)}}){% endif %}{% endif %}
        {% endfor %}
        {% endif %}
      {% endfor %}
    {% endfor %}