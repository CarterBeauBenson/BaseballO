"""Operational build boundaries; no metric meanings or source admissions."""

OFFENSE = frozenset({
    'tfs', 'paq-2', 'paq-a', 'offensive-reach', 'hidden-help-rate',
    'rally-kill-rate', 'rally-kill-severity', 'opportunity-erosion',
    'empty-game-rate', 'empty-game-damage', 'contribution-path-diversity',
    'recovery-quality', 'run-construction-depth', 'run-construction-breadth',
})
FAMILIES = {
    'offense': OFFENSE,
    'defense': frozenset({'resolution-depth', 'defender-breadth'}),
    'combined': frozenset({'paq-2.1'}),
    'other': frozenset({'adjudication-volatility', 'review-dependence-rate', 'role-realization-breadth'}),
}
ADMISSIONS = {
    'offense': ('batting_admission', 'scoring_run_admission', 'runner_resolution_admission',
                'pitch_count_admission', 'runner_boundary_admission'),
    'defense': ('batting_admission', 'scoring_run_admission', 'defensive_admission'),
    'combined': ('batting_admission', 'scoring_run_admission', 'runner_resolution_admission',
                 'pitch_count_admission', 'runner_boundary_admission', 'defensive_admission'),
    'other': ('batting_admission', 'scoring_run_admission'),
}


def owner(metric):
    return next(family for family, metrics in FAMILIES.items() if metric in metrics)


def initialize(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS dashboard_family_checkpoint (
        family TEXT NOT NULL, graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
        input_sha256 TEXT NOT NULL, PRIMARY KEY(family,graph_iri));
      CREATE TABLE IF NOT EXISTS dashboard_family_player_partition (
        family TEXT NOT NULL, graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
        input_sha256 TEXT NOT NULL, PRIMARY KEY(family,graph_iri));
      CREATE TABLE IF NOT EXISTS dashboard_evidence_checkpoint (
        graph_iri TEXT PRIMARY KEY REFERENCES game_dimension(graph_iri),
        rdf_sha256 TEXT NOT NULL, query_sha256 TEXT NOT NULL, row_count INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS dashboard_family_player_game (
        family TEXT NOT NULL, graph_iri TEXT NOT NULL REFERENCES game_dimension(graph_iri),
        player TEXT NOT NULL, team TEXT NOT NULL, plate_appearances INTEGER,
        roster_complete INTEGER NOT NULL, PRIMARY KEY(family,graph_iri,player));
    ''')
