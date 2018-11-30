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
        - :doc:`../analytics/{{analytic.id}}`
        {% endfor %}
        {% endif %}
      {% endfor %}
    {% endfor %}