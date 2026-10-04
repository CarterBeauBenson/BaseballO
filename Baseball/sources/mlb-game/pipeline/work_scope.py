"""Operational work selection. Archived games and their evidence stay intact.

User decision, 2026-10-04: retire spring training and WBC work. MLB's
exhibition games include preseason/WBC warmups. W means World Series,
not World Baseball Classic; WBC and its qualifiers use leagues 160/159.
This policy changes job selection, never the meaning of an existing graph.
"""
from functools import lru_cache
import json
from pathlib import Path

POLICY = 'mlb-active-work-without-spring-training-or-wbc-2026-10-04'
WBC_LEAGUES = {'159', '160'}


def exclusion_reason(record):
    data = record.get('gameData', record)
    game_type = record.get('gameType') or data.get('game', {}).get('type')
    if game_type == 'S':
        return 'spring-training'
    if game_type == 'E':
        return 'exhibition-including-preseason-and-wbc-warmups'
    teams = data.get('teams', {})
    for side in ('home', 'away'):
        team = teams.get(side, {})
        team = team.get('team', team)
        if str(team.get('league', {}).get('id', '')) in WBC_LEAGUES:
            return 'world-baseball-classic'
    if str(record.get('leagueId', '')) in WBC_LEAGUES:
        return 'world-baseball-classic'
    return None


@lru_cache(maxsize=4)
def _excluded(signature):
    result = {}
    for filename, _, _ in signature:
        batch = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
        for row in batch.get('games', []):
            reason = exclusion_reason(row)
            if reason:
                result[str(row['gamePk'])] = reason
        # New batches keep compact classifications even for unrequested games.
        for row in batch.get('excludedGames', []):
            result[str(row['gamePk'])] = row['reason']
    return result


def excluded_games(state):
    """Use existing compact schedule metadata, without reading/rebuilding RDF."""
    paths = sorted((Path(state)/'pipeline/control/mlb-game/batches').glob('*.json'))
    signature = tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
    return dict(_excluded(signature))


def active(state, game_pk):
    return str(game_pk) not in excluded_games(state)
