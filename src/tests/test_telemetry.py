import importlib.util
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'projects/f1-telemetry-analysis'))

class TelemetryTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('analytics')
        self.assertIsNotNone(spec, 'Distance alignment must be available independently of the page')
        import analytics
        self.a = analytics

    def lap(self, times=(0, 1, 2), distance=(0, 100, 200)):
        return pd.DataFrame({'Distance': distance, 'Time': pd.to_timedelta(times, unit='s'),
                             'Speed': [360]*3, 'Throttle': [100]*3, 'Brake': [False]*3, 'nGear': [8]*3})

    def test_identical_laps_zero_delta(self):
        aligned = self.a.align_laps(self.lap(), self.lap())
        self.assertEqual(aligned['Distance'].iloc[-1], 200)
        self.assertLess(abs(aligned['Delta']).max(), 1e-8)
        self.assertEqual(aligned['Gear1'].iloc[0], 8)

    def test_one_second_slower_lap_and_overlap(self):
        aligned = self.a.align_laps(self.lap((10, 11.5, 13)), self.lap())
        self.assertAlmostEqual(aligned['Delta'].iloc[-1], 1.0)
        shifted = self.lap(distance=(50, 100, 150))
        overlap = self.a.align_laps(self.lap(), shifted)
        self.assertEqual(overlap['Distance'].iloc[0], 50)
        self.assertEqual(overlap['Distance'].iloc[-1], 150)

    def test_unsorted_duplicates_and_boolean_brake(self):
        lap = self.lap((2,0,1), (200,0,100))
        lap.loc[1, 'Brake'] = True
        aligned = self.a.align_laps(pd.concat([lap,lap.iloc[[0]]]), self.lap())
        self.assertEqual(aligned['Brake1'].iloc[0],100)
        self.assertTrue(np.isfinite(aligned['Delta']).all())

    def test_missing_sector_is_unavailable(self):
        self.assertIsNone(self.a.seconds_delta(pd.NaT, pd.Timedelta(seconds=2)))

    def test_insufficient_and_mixed_stints_not_fitted(self):
        laps = pd.DataFrame({'LapTime':pd.to_timedelta([90,91,92,93],unit='s'),
           'TyreLife':[1,2,3,4], 'Stint':[1]*4,'Compound':['SOFT']*4})
        self.assertEqual(self.a.degradation(laps), [])

    def test_deleted_laps_do_not_count_toward_stint_minimum(self):
        laps=pd.DataFrame({'LapTime':pd.to_timedelta([90,91,92,93,94],unit='s'),'TyreLife':[1,2,3,4,5],'Stint':[1]*5,'Compound':['SOFT']*5,'Deleted':[False]*4+[True]})
        self.assertEqual(self.a.degradation(laps),[])

    def test_corner_labels_come_from_metadata(self):
        corners = pd.DataFrame({'Number':[4], 'Letter':['A'], 'Distance':[100]})
        table = self.a.corner_comparison(self.a.align_laps(self.lap(),self.lap()),corners)
        self.assertEqual(table.iloc[0]['Corner'],'T4A')
        self.assertIsNone(table.iloc[0]['Braking delta (m)'])

if __name__ == '__main__': unittest.main()
