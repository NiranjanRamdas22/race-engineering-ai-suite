import importlib.util
import unittest
from pathlib import Path
import socket
ROOT=Path(__file__).resolve().parents[2]
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'launcher.py').exists(),'Suite launcher missing')
        spec=importlib.util.spec_from_file_location('suite_launcher',ROOT/'launcher.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
    def test_occupied_unready_port_is_not_launched_over(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));s.listen();port=s.getsockname()[1]
            service={'port':port,'health':'/api/health','title':'Test','cwd':ROOT,'args':['nothing']}
            with self.assertRaisesRegex(RuntimeError,'occupied'):self.m.start_service('test',service)
    def test_port_map_is_unique_and_commands_use_workspace(self):
        ports=[s['port'] for s in self.m.SERVICES.values()]
        self.assertEqual(len(set(ports)),6)
        self.assertEqual(self.m.SERVICES['telemetry']['port'],8502)
        self.assertEqual(self.m.SERVICES['predictor']['port'],8501)
if __name__=='__main__':unittest.main()
