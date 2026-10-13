"""Deterministic, rate-limited radio coaching with optional bounded API calls."""
import time
from collections import deque, OrderedDict

class RaceEngineerAI:
    PRIORITY={'Low':1,'Medium':2,'High':3,'Critical':4}
    def __init__(self,api_key=None,provider='openai'):
        self.api_key=api_key;self.provider=provider;self.history=deque(maxlen=15);self.cooldowns=OrderedDict();self.engine='Rules';self.fallback_reason=None
    def reset(self):
        self.history.clear();self.cooldowns.clear()
    def generate_radio_message(self,events,current_state):
        now=float(current_state.get('timestamp',time.monotonic()));corner=current_state.get('corner','Unknown')
        candidates=[]
        for event in events:
            key=(event['event'],corner);priority=self.PRIORITY.get(event.get('urgency'),1)
            previous=self.cooldowns.get(key)
            if previous and now-previous[0]<5 and priority<=previous[1]:continue
            candidates.append((priority,event,key))
        if not candidates:return ''
        priority,event,key=max(candidates,key=lambda x:x[0]);self.cooldowns[key]=(now,priority);self.cooldowns.move_to_end(key)
        while len(self.cooldowns)>128:self.cooldowns.popitem(last=False)
        self.history.append(event)
        kind=event['event'];fallback={'wheel_lockup':f'Lockup in {corner}. Ease brake pressure.','tire_overheat':'Tyre temperature elevated. Reduce sliding and monitor cooling.','time_loss':f'Time loss in {corner}. Compare braking and exit telemetry.'}.get(kind,event.get('detail','Monitor telemetry.'))
        self.engine='Rules';self.fallback_reason=None
        if not self.api_key:return fallback
        try:
            from openai import OpenAI
            response=OpenAI(api_key=self.api_key,timeout=4,max_retries=0).chat.completions.create(model='gpt-4o',messages=[{'role':'system','content':'Give one short race-radio instruction using only supplied measurements. Do not invent metres, diagnoses or strategy.'},{'role':'user','content':str(event)}],max_tokens=80)
            self.engine='OpenAI gpt-4o';return response.choices[0].message.content or fallback
        except Exception:
            self.fallback_reason='AI service unavailable';return fallback
