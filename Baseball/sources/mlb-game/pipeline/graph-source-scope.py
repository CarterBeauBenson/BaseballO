"""Q6 scopes existing source diagnostics for graph conformance, not metrics.

Keep the source census unchanged. Incomplete plays and absent inning totals
withhold complete populations, but do not preclude checking independent RDF.
All other non-clock source disagreements still prevent graph admission.
"""


DECISION = 'archive/design-records/mlb-game-quarantine-boundaries/review.json'


def graph_blocking_issues(issues):
    def completeness_only(issue):
        return (issue.get('code') == 'INCOMPLETE_SOURCE_PLAY'
                or (issue.get('code') == 'INNING_RUN_TOTAL_MISMATCH'
                    and 'reported' in issue and issue['reported'] is None))

    # T1 already isolates contradictory clock pairs; their exact omissions and
    # preserved event structure remain checked by the clock SHACL profile.
    return [issue for issue in issues
            if issue.get('code') not in {'REVERSED_PLAY_TIMES', 'REVERSED_EVENT_TIMES'}
            and not completeness_only(issue)]
