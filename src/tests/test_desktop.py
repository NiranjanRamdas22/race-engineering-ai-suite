import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'projects/ai-race-engineer/ai_race_engineer'))
from sim_emulator import SimEmulator
from race_engineer_ai import RaceEngineerAI

class DesktopTests(unittest.TestCase):
    def test_recorded_run_uses_reference_delta_and_optional_tyre_data(self):
        from runtime import EngineerRuntime
        from motorsport.recorded import Recording
        samples=[dict(timestamp=t,distance=d,speed=100,throttle=1,brake=0,gear=3,tire_temps={'FL':90},tire_wear={'FL':98}) for t,d in [(0,0),(1,100),(2,200)]]
        r=EngineerRuntime();r.recording=Recording(samples);r.set_reference(Recording(samples))
        frame,events=r.recorded_frame(1)
        self.assertEqual(frame['lap_delta'],0);self.assertEqual(frame['tire_wear']['FL'],98)
        self.assertEqual(events,[])
        r.reset();self.assertIsNone(r.reference_analysis.previous);r.close()

    def test_full_audio_queue_keeps_urgent_message(self):
        import queue
        from runtime import offer
        q=queue.PriorityQueue(2);offer(q,(-4,1,0,'urgent'));offer(q,(-1,2,0,'low'));offer(q,(-2,3,0,'medium'))
        self.assertEqual(q.get()[-1],'urgent');self.assertEqual(q.get()[-1],'medium')
    def test_runtime_reset_discards_pending_messages(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('runtime'),'Worker runtime missing')
        from runtime import EngineerRuntime
        r=EngineerRuntime();r.results.put((r.generation,'radio','old'));r.reset()
        self.assertTrue(r.results.empty());self.assertEqual(r.generation,1)
        r.close()

    def test_ten_thousand_frames_bound_tire_state(self):
        sim=SimEmulator()
        for _ in range(10000):
            f=sim.get_telemetry_frame()
            self.assertTrue(all(0<=v<=100 for v in f['tire_wear'].values()),f)
            self.assertTrue(all(20<=v<=150 for v in f['tire_temps'].values()),f)

    def test_repeat_warning_cooldown_and_urgent_priority(self):
        ai=RaceEngineerAI()
        state={'corner':'T1','timestamp':1}
        e={'event':'tire_overheat','urgency':'Medium','detail':'Hot'}
        self.assertTrue(ai.generate_radio_message([e],state))
        self.assertEqual(ai.generate_radio_message([e],dict(state,timestamp=2)),'')
        urgent={'event':'wheel_lockup','urgency':'High','detail':'Lockup'}
        message=ai.generate_radio_message([e,urgent],dict(state,timestamp=3))
        self.assertIn('lockup',message.lower())

if __name__=='__main__':unittest.main()
