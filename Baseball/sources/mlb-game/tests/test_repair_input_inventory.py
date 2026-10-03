"""One bad or early input must not starve other targeted RML repairs."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_targeted_award_addition import W
from test_targeted_defensive_addition import D


class RepairInputInventory(unittest.TestCase):
    def prepare(self,state):
        repo=state/'repo';source=repo/'data/raw/42.json'
        W.atomic(source,dict(gamePk=42,liveData=dict(plays=dict(allPlays=[
            dict(result=dict(eventType='intent_walk'),playEvents=[{}]*5)]))))
        W.atomic(state/'pipeline/control/mlb-game/award-addition/822864.json',dict(status='complete'))
        return repo,source

    def test_unchanged_input_is_revisited_after_first_graph_promotion(self):
        for name,worker in [('award',W),('defensive',D)]:
            with self.subTest(worker=name),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);repo,source=self.prepare(state)
                selected=[dict(atBatIndex='7')] if name=='award' else dict(acts=[{}])
                with patch.object(worker,'ROOT',repo),patch.object(worker,'fingerprint',return_value='stable'), \
                        patch.object(worker,'select',return_value=selected) as select:
                    self.assertIsNone(worker.next_witness(state));select.assert_not_called()
                    (state/'pipeline/evidence/nifi/game-promotion/42').mkdir(parents=True)
                    self.assertEqual(worker.next_witness(state)['path'],str(source))
                    select.assert_called_once()

    def test_malformed_and_retired_inputs_do_not_abort_inventory(self):
        for name,worker in [('award',W),('defensive',D)]:
            with self.subTest(worker=name),tempfile.TemporaryDirectory() as temp:
                state=Path(temp);repo,source=self.prepare(state)
                broken=source.with_name('000.json');broken.write_bytes(b'{broken')
                retired=source.with_name('001.json');retired.write_bytes(b'{}')
                (state/'pipeline/evidence/nifi/game-promotion/42').mkdir(parents=True)
                selected=[dict(atBatIndex='7')] if name=='award' else dict(acts=[{}])
                original=Path.read_bytes
                def read(path):
                    if path==retired:raise FileNotFoundError('retired after stat')
                    return original(path)
                with patch.object(worker,'ROOT',repo),patch.object(worker,'fingerprint',return_value='stable'), \
                        patch.object(worker,'select',return_value=selected),patch.object(Path,'read_bytes',read):
                    self.assertEqual(worker.next_witness(state)['path'],str(source))
                inventory=W.read(state/f'pipeline/control/mlb-game/{name}-addition/inventory.json')
                self.assertEqual(inventory['inputs'][str(broken)]['status'],'invalid-input')
                self.assertEqual(broken.read_bytes(),b'{broken')


if __name__=='__main__':unittest.main()
