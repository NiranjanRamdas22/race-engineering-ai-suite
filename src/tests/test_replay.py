import importlib.util
import sys
import unittest
import asyncio,time,threading
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'projects/ai-replay-engineer/ai_replay_engineer'
sys.path.insert(0,str(FOLDER))
spec=importlib.util.spec_from_file_location('replay_server',FOLDER/'server.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)

class ReplayTests(unittest.TestCase):
    def test_malformed_input_closes_cleanly(self):
        with TestClient(server.app) as client:
            with client.websocket_connect('/ws/telemetry') as ws:
                ws.send_text('{broken')
                message=ws.receive()
                self.assertEqual(message.get('type'),'websocket.send')
                import json
                self.assertEqual(json.loads(message['text'])['type'],'ERROR')
                self.assertEqual(ws.receive()['code'],1008)
    def test_reset_has_new_session_and_zero_sequence(self):
        with TestClient(server.app) as client:
            with client.websocket_connect('/ws/telemetry') as ws:
                ws.send_json({'type':'RESET','session_id':'test-one'})
                reply=ws.receive_json()
                self.assertEqual(reply['type'],'RESET_ACK')
                self.assertEqual(reply['session_id'],'test-one');self.assertEqual(reply['seq'],0)
    def test_reference_is_full_and_honestly_labelled(self):
        with TestClient(server.app) as client:
            data=client.get('/api/reference-lap').json()
            self.assertIn('provenance',data);self.assertGreater(len(data.get('samples',[])),120)

    def test_delayed_coaching_does_not_block_frames_or_escape_reset(self):
        started=threading.Event();cancelled=threading.Event()
        async def delayed(alert,model):
            started.set()
            try:await asyncio.sleep(5)
            except asyncio.CancelledError:cancelled.set();raise
            return 'STALE ANSWER','AI',None
        with patch.object(server,'coaching',delayed),TestClient(server.app) as client:
            with client.websocket_connect('/ws/telemetry') as ws:
                ws.send_json({'type':'RESET','session_id':'old'});ws.receive_json()
                sample=server.reference.at_time(1);sample['speed']=0
                ws.send_json({'type':'FRAME','session_id':'old','seq':1,'sample':sample})
                self.assertEqual(ws.receive_json()['type'],'FRAME_UPDATE');self.assertTrue(started.wait(1))
                tick=time.monotonic()
                sample=server.reference.at_time(2);sample['speed']=0
                ws.send_json({'type':'FRAME','session_id':'old','seq':2,'sample':sample})
                self.assertEqual(ws.receive_json()['type'],'FRAME_UPDATE');self.assertLess(time.monotonic()-tick,1)
                self.assertEqual(client.get('/api/health').status_code,200)
                ws.send_json({'type':'RESET','session_id':'new'})
                self.assertEqual(ws.receive_json()['session_id'],'new');self.assertTrue(cancelled.wait(1))
                ws.send_json({'type':'FRAME','session_id':'new','seq':1,'sample':server.reference.at_time(1)})
                reply=ws.receive_json();self.assertEqual(reply['type'],'FRAME_UPDATE');self.assertEqual(reply['session_id'],'new')

if __name__=='__main__':unittest.main()
