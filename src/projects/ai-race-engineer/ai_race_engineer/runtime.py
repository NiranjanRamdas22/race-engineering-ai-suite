"""Bounded worker queues. Tkinter is accessed only by the GUI's main thread."""
import threading
import queue
import time
import sys
import json
import heapq
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from motorsport.recorded import Recording,SessionAnalysis
from sim_emulator import SimEmulator
from driving_events import AnalysisEngine
from race_engineer_ai import RaceEngineerAI

def offer(q,item):
    if isinstance(q,queue.PriorityQueue):
        with q.mutex:
            items=q.queue+[item]
            items=sorted(items)[:q.maxsize]
            q.queue[:]=items;heapq.heapify(q.queue);q.not_empty.notify()
        return
    try:q.put_nowait(item)
    except queue.Full:
        try:q.get_nowait()
        except queue.Empty:pass
        try:q.put_nowait(item)
        except queue.Full:pass

def clear(q):
    while True:
        try:q.get_nowait()
        except queue.Empty:return

class EngineerRuntime:
    def __init__(self):
        self.lock=threading.RLock();self.stop=threading.Event();self.playing=False;self.generation=0
        self.results=queue.Queue(32);self.coaching=queue.Queue(1);self.audio=queue.PriorityQueue(8)
        self.sim=SimEmulator();self.engine=AnalysisEngine();self.ai=RaceEngineerAI();self.recording=None;self.reference_analysis=None
        self.playback_speed=1;self.elapsed=0;self.voice=False;self.volume=80;self.effects=False;self.prev=None;self.threads=[]
    def start_workers(self):
        for target in (self.telemetry_loop,self.ai_loop,self.audio_loop):
            thread=threading.Thread(target=target,daemon=True);thread.start();self.threads.append(thread)
    def reset(self,scenario='Balanced'):
        with self.lock:
            self.generation+=1;self.playing=False;self.sim=SimEmulator(scenario=scenario);self.prev=None;self.elapsed=0;self.ai=RaceEngineerAI(api_key=self.ai.api_key)
            if self.reference_analysis:self.reference_analysis.reset()
            for q in (self.results,self.coaching,self.audio):clear(q)
    def load_recording(self,path):
        payload=json.loads(Path(path).read_text(encoding='utf-8-sig'));recording=Recording(payload['samples'],payload.get('provenance'))
        self.reset()
        with self.lock:
            self.recording=recording
            if self.reference_analysis:self.reference_analysis.recording=recording
    def set_reference(self,recording):
        self.reset()
        with self.lock:self.reference_analysis=SessionAnalysis(recording,recording=self.recording)
    def use_simulation(self):
        with self.lock:self.recording=None;self.reference_analysis=None
        self.reset()
    def recorded_frame(self,elapsed):
        s=self.recording.at_time(elapsed);comparison=None
        if self.reference_analysis:
            try:comparison=self.reference_analysis.process(s)
            except ValueError:pass
        frame={**s,'rpm':None,'corner':f'Recorded distance {s["distance"]:.0f} m','throttle':s['throttle']*100,'brake':s['brake']*100,'tire_temps':s.get('tire_temps',{}),'tire_wear':s.get('tire_wear',{}),'lap_delta':comparison['time_delta'] if comparison else None,'braking_offset_m':comparison['braking_offset_m'] if comparison else None,'lateral_offset':comparison['lateral_offset'] if comparison else None,'mode':'recorded'}
        events=[{'event':a['type'],'urgency':a['severity'].title(),'detail':a['msg']} for a in comparison['alerts']] if comparison else []
        return frame,events
    def telemetry_loop(self):
        last=time.monotonic()
        while not self.stop.wait(.1):
            now=time.monotonic();dt=now-last;last=now
            with self.lock:
                if not self.playing:continue
                generation=self.generation
                if self.recording:
                    self.elapsed=min(self.recording.time[-1],self.elapsed+dt*self.playback_speed)
                    frame,events=self.recorded_frame(self.elapsed)
                    if self.elapsed>=self.recording.time[-1]:self.playing=False
                else:
                    frame=self.sim.get_telemetry_frame();events=self.engine.analyze_frame(frame,self.prev)
                self.prev=frame
                offer(self.results,(generation,'frame',frame))
                if events:offer(self.coaching,(generation,events,frame))
    def ai_loop(self):
        while not self.stop.is_set():
            try:g,events,frame=self.coaching.get(timeout=.1)
            except queue.Empty:continue
            with self.lock:
                if g!=self.generation:continue
                ai=self.ai
            message=ai.generate_radio_message(events,frame)
            with self.lock:
                if message and g==self.generation:
                    severity=max((e['urgency'] for e in events),key=lambda s:ai.PRIORITY.get(s,1))
                    offer(self.results,(g,'radio',{'text':message,'severity':severity,'time':frame['timestamp'],'engine':ai.engine}))
                    if self.voice:offer(self.audio,(-ai.PRIORITY[severity],time.monotonic(),g,message))
    def audio_loop(self):
        voice=None
        try:
            import comtypes
            import comtypes.client
            comtypes.CoInitialize();voice=comtypes.client.CreateObject('SAPI.SpVoice')
        except Exception:pass
        try:
            while not self.stop.is_set():
                try:priority,when,g,text=self.audio.get(timeout=.1)
                except queue.Empty:
                    if voice and not self.voice:voice.Speak('',2)
                    continue
                if not self.voice or g!=self.generation:continue
                if not voice:
                    offer(self.results,(g,'status','Windows speech unavailable. Install the desktop dependencies.'));continue
                voice.Volume=int(self.volume)
                if self.effects:
                    import winsound
                    winsound.Beep(1000,60)
                voice.Speak(text,1)
                while voice.Status.RunningState==2 and not self.stop.wait(.05):
                    urgent=not self.audio.empty() and self.audio.queue[0][0]<priority
                    if not self.voice or g!=self.generation or urgent:
                        voice.Speak('',2);break
        finally:
            if voice:
                voice.Speak('',2);comtypes.CoUninitialize()
    def close(self):
        self.stop.set()
        for thread in self.threads:thread.join(timeout=5)

