import sys,json,asyncio,time,threading,ctypes,os,psutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'projects/ai-race-engineer/ai_race_engineer'))
from gui_dashboard import RaceEngineerGUI
import httpx,websockets
REPORT=ROOT/'.implementation/soak.json';duration=float(os.environ.get('SOAK_SECONDS','1800'));started=time.monotonic();metrics={'duration_requested':duration,'frames':0,'replay_resets':0,'desktop_resets':0,'failures':[],'samples':[]};stop=threading.Event()
replay_pid=json.loads((ROOT/'.runtime/processes.json').read_text()).get('replay',{}).get('pid')
async def replay():
    try:
        async with httpx.AsyncClient() as client:reference=(await client.get('http://127.0.0.1:8001/api/reference-lap')).json()
        samples=reference['samples'];seq=0;i=0;session='soak-0'
        async with websockets.connect('ws://127.0.0.1:8001/ws/telemetry') as ws:
            await ws.send(json.dumps({'type':'RESET','session_id':session}));await ws.recv()
            while not stop.is_set() and time.monotonic()-started<duration:
                if i>=len(samples):
                    i=0;seq=0;metrics['replay_resets']+=1;session='soak-'+str(metrics['replay_resets'])
                    await ws.send(json.dumps({'type':'RESET','session_id':session}));reply=json.loads(await ws.recv());assert reply['type']=='RESET_ACK'
                seq+=1
                await ws.send(json.dumps({'type':'FRAME','session_id':session,'seq':seq,'sample':samples[i]}));reply=json.loads(await ws.recv());assert reply['type']=='FRAME_UPDATE' and reply['session_id']==session
                assert abs(reply['time_delta'])<1e-7
                metrics['frames']+=1;i+=1
                await asyncio.sleep(.1)
    except Exception as exc:metrics['failures'].append('Replay: '+repr(exc));stop.set()
thread=threading.Thread(target=lambda:asyncio.run(replay()),daemon=True);thread.start()
app=RaceEngineerGUI();app.root.withdraw();app.runtime.playing=True
last_minute=-1
class Memory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
def sample():
    global last_minute
    elapsed=time.monotonic()-started;minute=int(elapsed//60)
    if minute!=last_minute:
        last_minute=minute
        metrics['samples'].append({'elapsed':round(elapsed,1),'memory_mb':round(psutil.Process().memory_info().rss/1048576,2),'threads':threading.active_count(),'radio_history':len(app.history),'results_queue':app.runtime.results.qsize(),'ai_queue':app.runtime.coaching.qsize(),'audio_queue':app.runtime.audio.qsize(),'tyre_temps':dict(app.runtime.sim.tire_temps),'tyre_remaining':dict(app.runtime.sim.tire_wear)})
        if replay_pid:metrics['samples'][-1]['replay_server_memory_mb']=round(psutil.Process(replay_pid).memory_info().rss/1048576,2)
        metrics['samples'][-1]['log_bytes']=sum(p.stat().st_size for p in (ROOT/'.runtime').glob('*.log'))
        if minute and minute%5==0:app.reset();app.start();metrics['desktop_resets']+=1
        metrics['elapsed_seconds']=round(elapsed,1);REPORT.write_text(json.dumps(metrics,indent=2))
    if elapsed>=duration or stop.is_set():
        stop.set();app.close();thread.join(5);metrics['elapsed_seconds']=round(time.monotonic()-started,1);metrics['complete']=metrics['elapsed_seconds']>=duration and not metrics['failures'];REPORT.write_text(json.dumps(metrics,indent=2));return
    app.root.after(1000,sample)
app.root.after(1000,sample);app.mainloop()
