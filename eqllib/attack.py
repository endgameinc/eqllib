from collections import defaultdict
import json
import os

attack = {}

techniques = {}
tactics = []


def build_attack():
    global attack, techniques, tactics
    if attack:
        return attack, techniques, tactics

    with open(os.path.join(os.path.dirname(__file__), 'enterprise-attack.json'), 'r') as f:
        attack.update(json.load(f))

    # Populate the ATT&CK matrix
    for obj in attack.get('objects', []):
        if obj['type'] == 'attack-pattern':
            for reference in obj['external_references']:
                if reference.get('source_name') == 'mitre-attack':
                    technique_id = reference['external_id']
                    techniques[technique_id] = obj
                    for phase in obj['kill_chain_phases']:
                        if phase['kill_chain_name'] == 'mitre-attack':
                            tactic_name = phase['phase_name']
                        break

        if obj['type'] == 'x-mitre-tactic':
            tactics.append(obj)

    # Sort the tactics by the order ATT&CK uses
    tactics.sort(key=lambda tactic: int(tactic['external_references'][0]['external_id'][2:]))
    return attack, techniques, tactics


def get_matrix(platform=None):
    if not attack:
        build_attack()

    matrix_lookup = defaultdict(list)

    # Populate the ATT&CK matrix
    for obj in attack.get('objects', []):
        if obj['type'] == 'attack-pattern':
            if platform and platform not in obj.get("x_mitre_platforms", []):
                continue

            for reference in obj['external_references']:
                if reference.get('source_name') == 'mitre-attack':
                    technique_id = reference['external_id']
                    for phase in obj['kill_chain_phases']:
                        if phase['kill_chain_name'] == 'mitre-attack':
                            tactic_name = phase['phase_name']
                            matrix_lookup[tactic_name].append(technique_id)
                        break

    # Now build the cells of the matrix
    matrix_height = max(len(column) for column in matrix_lookup.values())
    matrix_cells = []
    for row_number in range(matrix_height):
        current_row = []
        for tactic in tactics:
            shortname = tactic['x_mitre_shortname']
            if row_number < len(matrix_lookup[shortname]):
                current_row.append(techniques[matrix_lookup[shortname][row_number]])
            else:
                current_row.append(None)
        matrix_cells.append(current_row)

    return matrix_cells
