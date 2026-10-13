import importlib.util
import unittest
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'projects/race-result-predictor/race_result_predictor'
def module(name):
    spec=importlib.util.spec_from_file_location(name,FOLDER/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PredictorTests(unittest.TestCase):
    def test_invalid_metadata_is_not_available_to_ui(self):
        import tempfile
        m=module('model_io')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'model_metadata.json'
            for value in ('{broken','[]','{"schema_version":1,"mode":"historical"}'):
                p.write_text(value)
                self.assertIsNone(m.load_metadata(tmp))
    def test_corrupt_model_artifact_is_unavailable(self):
        import tempfile,json
        m=module('model_io')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'model_metadata.json').write_bytes((FOLDER/'model_metadata.json').read_bytes());(p/'rank_model.pkl').write_bytes(b'not a model')
            bundle,reason=m.load_bundle(p);self.assertIsNone(bundle);self.assertIn('unavailable',reason.lower())
    def test_missing_artifacts_return_actionable_unavailable_state(self):
        self.assertTrue((FOLDER/'model_io.py').exists(),'Model availability handling missing')
        import tempfile
        m=module('model_io')
        with tempfile.TemporaryDirectory() as tmp:
            bundle,reason=m.load_bundle(Path(tmp))
            self.assertIsNone(bundle);self.assertIn('train',reason.lower())
    def test_team_form_cannot_use_same_race_teammate_result(self):
        m=module('model_trainer');df=pd.DataFrame([{'season':2023,'raceId':r,'driverId':d,'constructorId':'team','position_res':p,'position_qual':p} for r,d,p in [(1,'a',2),(1,'b',4),(2,'a',1),(2,'b',3),(3,'a',5),(3,'b',7)]])
        before=m.RacePredictorTrainer(df).engineer_features(df.copy());changed=df.copy();changed.loc[(changed.raceId==2)&(changed.driverId=='a'),'position_res']=20
        after=m.RacePredictorTrainer(changed).engineer_features(changed)
        one=before[before.raceId==2].set_index('driverId');two=after[after.raceId==2].set_index('driverId')
        self.assertEqual(one.loc['b','team_rolling_perf'],two.loc['b','team_rolling_perf'])
        self.assertEqual(one.loc['a','team_rolling_perf'],3)
    def test_nested_jolpica_results_parse(self):
        m=module('data_pipeline');p=m.F1DataPipeline()
        self.assertTrue(hasattr(p,'parse_races'),'Nested API parsing missing')
        data={'MRData':{'RaceTable':{'Races':[{'season':'2024','round':'1','raceName':'Race','date':'2024-03-01','Circuit':{'circuitId':'test','circuitName':'Test','Location':{'country':'Test'}},'Results':[{'position':'1','grid':'2','points':'25','Driver':{'driverId':'a','givenName':'A','familyName':'Driver'},'Constructor':{'constructorId':'team','name':'Team'},'status':'Finished'}]}]}}}
        rows=p.parse_races(data,'Results');self.assertEqual(rows[0]['position_res'],1);self.assertEqual(rows[0]['driverName'],'A Driver')
    def test_strategy_uses_stints_and_pit_loss(self):
        self.assertTrue((FOLDER/'strategy.py').exists(),'Strategy calculator missing')
        m=module('strategy');one=m.scenario_time(10,90,[5],20,[.2,.2]);two=m.scenario_time(10,90,[3,7],20,[.2,.2,.2])
        self.assertAlmostEqual(one['total_seconds'],924)
        self.assertAlmostEqual(two['total_seconds'],942.4)
        with self.assertRaises(ValueError):m.scenario_time(10,90,[7,3],20,[.2]*3)
if __name__=='__main__':unittest.main()
