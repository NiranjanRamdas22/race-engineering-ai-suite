import importlib.util
import unittest

class RecordedTests(unittest.TestCase):
    def test_unmatched_braking_zone_is_unavailable(self):
        ref=self.Recording(self.samples());run=self.samples()
        for s in run:s['distance']+=250
        # Extra braking application must not be paired with a different corner.
        reference=self.samples()+[dict(self.samples()[-1],timestamp=6,distance=650)]
        analysis=self.Analysis(self.Recording(reference),recording=self.Recording(run))
        analysis.process(run[1]);result=analysis.process(run[2])
        self.assertIsNone(result['braking_offset_m'])
        self.assertFalse(any(a['type'].startswith('BRAKING') for a in result['alerts']))
    def test_provenance_must_be_an_object(self):
        with self.assertRaises(ValueError):self.Recording(self.samples(),provenance=['invalid'])
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('motorsport'),'Shared recorded telemetry schema missing')
        from motorsport.recorded import Recording,SessionAnalysis
        self.Recording=Recording;self.Analysis=SessionAnalysis
    def samples(self):
        return [{'timestamp':t,'distance':d,'speed':100,'throttle':1 if b==0 else 0,'brake':b,'gear':3} for t,d,b in [(0,0,0),(1,100,0),(2,200,1),(3,300,0),(4,400,0)]]
    def test_delta_uses_elapsed_time_not_speed(self):
        ref=self.Recording(self.samples());a=self.Analysis(ref)
        sample=dict(self.samples()[3],timestamp=4)
        self.assertAlmostEqual(a.process(sample)['time_delta'],1)
    def test_invalid_samples_rejected(self):
        from math import nan
        for field,value in [('speed',nan),('throttle',101),('gear',99)]:
            samples=self.samples();samples[1][field]=value
            with self.assertRaises(ValueError):self.Recording(samples)
        with self.assertRaises(ValueError):self.Recording(list(reversed(self.samples())))
    def test_braking_offset_is_measured_and_reset_clears_state(self):
        a=self.Analysis(self.Recording(self.samples()))
        a.process(dict(self.samples()[1],distance=80));sample=dict(self.samples()[2],brake=1,distance=180)
        result=a.process(sample)
        self.assertEqual(result['braking_offset_m'],-20)
        a.reset();self.assertIsNone(a.previous);self.assertEqual(len(a.cooldowns),0)
    def test_interpolation_matches_reference_between_samples(self):
        ref=self.Recording(self.samples());self.assertEqual(ref.at_distance(150)['timestamp'],1.5)
        self.assertEqual(ref.at_time(1.5)['distance'],150)

    def test_identical_interpolated_braking_has_no_false_warning(self):
        ref=self.Recording(self.samples());analysis=self.Analysis(ref)
        result=None
        for t in [1.0,1.29,1.41,1.8]:result=analysis.process(ref.at_time(t))
        self.assertFalse(any(a['type'].startswith('BRAKING') for a in result['alerts']))
        self.assertAlmostEqual(analysis.last_braking,0,places=6)

    def test_optional_tyre_channels_survive_timestamp_interpolation(self):
        samples=self.samples()
        for i,s in enumerate(samples):s.update(tire_temps={'FL':90+i*2},tire_wear={'FL':100-i})
        result=self.Recording(samples).at_time(1.5)
        self.assertEqual(result['tire_temps']['FL'],93)
        self.assertEqual(result['tire_wear']['FL'],98.5)

    def test_known_recording_uses_original_braking_samples_at_fast_playback(self):
        samples=[dict(timestamp=d/100,distance=d,speed=100,throttle=0,brake=b,gear=3) for d,b in [(0,0),(100,0),(190,0),(200,1),(250,1),(400,0)]]
        ref=self.Recording(samples);analysis=self.Analysis(ref,recording=ref)
        analysis.process(ref.at_distance(150));result=analysis.process(ref.at_distance(240))
        self.assertEqual(result['braking_offset_m'],0)
        self.assertEqual(result['alerts'],[])

if __name__=='__main__':unittest.main()
