"""The owner groups every exclusion without recalculating or changing it."""
import importlib.util
import unittest
from unittest.mock import patch
from test_metric_suite_serving import M, G1, G2, database
from test_player_ranges import P

spec=importlib.util.spec_from_file_location('empty_remainder',M.ROOT/'serving/empty_game_remainder.py')
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


class EmptyGameRemainder(unittest.TestCase):
    def test_every_exclusion_is_grouped_once_and_known_zero_is_complete(self):
        db=database();self.addCleanup(db.close);P.initialize(db)
        for graph in (G1,G2):
            M._blocks.store_game(M._block_api(),db,graph,[])
            M._blocks.store_metric(M._block_api(),db,graph,'empty-game-rate',dict(progressInputs=dict(
                plateAppearances=[],unresolvedPlateAppearances=[dict(plateAppearance='pa',
                    gaps=['UNRESOLVED_PROGRESS_ATTRIBUTION'],possiblePositivePlayers=['p1'])])))
            proof=M._json(dict(status='admitted'))
            db.execute('INSERT INTO metric_suite_runner_resolution_admission VALUES (?,?,?)',(graph,proof,M._hash(proof)))
        for graph,player,complete,reason,games in [(G1,'p1',0,'COMPLETE_EMPTY_GAME_CLASSIFICATION',1),
                (G2,'p1',0,'COMPLETE_EMPTY_GAME_CLASSIFICATION',1),(G1,'p2',0,'OFFENSIVE_ELIGIBILITY',0),
                (G1,'p3',1,None,1),(G1,'p4',1,None,0)]:
            db.execute('INSERT INTO dashboard_player_metric VALUES (?,?,?,?,?,?)',
                (graph,player,'empty-game-rate',complete,M._json(dict(kind='count',count=0,eligibleGames=games)),reason))
        before=db.total_changes
        with patch.object(M,'batting_progress_evidence',side_effect=AssertionError('report must not score')):
            result=R.summarize(M,db,'published-build')
        self.assertEqual(db.total_changes,before)
        self.assertEqual(result['publicationId'],'published-build')
        self.assertEqual(result['summary']['incompletePlayers'],2)
        self.assertEqual(result['summary']['incompletePlayerGames'],3)
        self.assertEqual(result['summary']['completeEligiblePlayers'],1)
        self.assertEqual({g['family']:g['playerGames'] for g in result['families']},
            {'UNRESOLVED_PROGRESS_ATTRIBUTION':2,'OFFENSIVE_ELIGIBILITY':1})
