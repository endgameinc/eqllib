.. include:: links.rst

======================
Atomic Blue Detections
======================


.. list-table::
    :header-rows: 1
    :class: analytic-table

    * - Analytic
      - Contributors
      - Updated
      - Tactics
      - Techniques

    {% for analytic in red_analytics | sort(attribute='name') %}
    * - :doc:`analytics/{{analytic.id}}`
      - {{analytic.metadata.contributors | join(", ") }}
      - {{analytic.metadata.updated_date }}
      - {% for tactic in analytic.metadata.tactics %}`{{tactic}}`_{{ "\n\n        " if not loop.last }}{% endfor %}
      - {% for tech_id in analytic.metadata.techniques %}`{{tech_id}}`_ {{techniques[tech_id]['name']}}{{  "\n\n        " if not loop.last }}{% endfor %}{% endfor %}
