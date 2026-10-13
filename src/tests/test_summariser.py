import importlib.util
import unittest
from pathlib import Path
import tempfile
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'projects/race-summariser/race_summariser/backend'

class SummariserTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('race_data_test',FOLDER/'race_data.py');self.data=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.data)
    def test_report_includes_pit_cycle_and_inherited_positions(self):
        race=self.data.RACES_DATABASE['monza_2024'];report=self.data.generate_analytical_debrief(race)
        strategic=report.split('Critical Strategic Decisions')[1].split('Chronological')[0]
        for event in race['key_timeline']:
            if event['type']=='PIT_CYCLE_GAIN':self.assertIn(event['title'],strategic)
        self.assertNotIn('## Critical Strategic Decisions\n\n##',report)
    def test_incomplete_import_stays_unknown_and_persists(self):
        spec=importlib.util.spec_from_file_location('race_store',FOLDER/'store.py') if (FOLDER/'store.py').exists() else None
        self.assertIsNotNone(spec,'Persistent validated race store missing')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'races.db';store=m.RaceStore(path);race=m.RaceRecord(race_id='test',name='Partial race',circuit='Circuit')
            store.save(race.model_dump());loaded=m.RaceStore(path).get('test')
            self.assertIsNone(loaded['winner']);self.assertIsNone(loaded['laps']);self.assertEqual(loaded['podium'],[]);self.assertTrue(loaded['incomplete'])
            with self.assertRaises(Exception):m.RaceRecord(race_id='bad',name='Test',circuit='Circuit',laps=-1)

if __name__=='__main__':unittest.main()
