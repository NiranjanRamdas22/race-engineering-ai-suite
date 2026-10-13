import importlib.util
from pathlib import Path
import unittest,struct
FOLDER=Path(__file__).resolve().parents[1]/'projects/ai-replay-engineer/ai_replay_engineer'
spec=importlib.util.spec_from_file_location('udp_parser',FOLDER/'f1_udp_parser.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class UDPTests(unittest.TestCase):
    def test_f123_packet_header_and_car_prefix(self):
        header=struct.pack('<HBBBBBQfIIBB',2023,23,1,0,1,6,12345,12.5,90,91,1,255)
        car=struct.pack('<HfffBbHBBH4H4B4BH4f4B',250,.75,-.1,.25,0,5,11000,1,80,255,*([500]*4),*([95]*4),*([90]*4),110,*([22.5]*4),*([0]*4))
        data=header+bytes(60)+car+bytes(60*20)+bytes(3);r=m.F1UDPReceiver()
        h=r.parse_header(data);self.assertEqual(h['session_uid'],12345);self.assertEqual(h['player_car_index'],1)
        f=r.parse_car_telemetry(data,1);self.assertEqual(f['speed'],250);self.assertAlmostEqual(f['brake'],.25);self.assertEqual(f['gear'],5)
    def test_truncated_and_unsupported_packets_rejected(self):
        r=m.F1UDPReceiver();self.assertIsNone(r.parse_header(b'bad'));self.assertIsNone(r.parse_car_telemetry(b'bad',0))
        data=struct.pack('<HBBBBBQfIIBB',2024,24,1,0,1,6,1,0,1,1,0,255)+bytes(1323)
        self.assertIsNone(r.parse_header(data))
if __name__=='__main__':unittest.main()
