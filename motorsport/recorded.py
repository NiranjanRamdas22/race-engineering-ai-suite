import math
from collections import OrderedDict
import numpy as np

FIELDS=('timestamp','distance','speed','throttle','brake','gear')
def validate_sample(sample):
    if not isinstance(sample,dict): raise ValueError('Telemetry must be an object.')
    output={}
    for field in FIELDS:
        value=sample.get(field)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError(f'{field} must be a finite number.')
        output[field]=float(value)
    for field in ('timestamp','distance','speed'):
        if output[field]<0: raise ValueError(f'{field} must be nonnegative.')
    if output['speed']>500: raise ValueError('speed exceeds supported range (500 km/h).')
    for field in ('throttle','brake'):
        if not 0<=output[field]<=1: raise ValueError(f'{field} must be normalized 0–1.')
    if output['gear']!=int(output['gear']) or not -1<=output['gear']<=8: raise ValueError('gear must be an integer from -1 to 8.')
    output['gear']=int(output['gear'])
    for field in ('x','y'):
        if field in sample:
            value=sample[field]
            if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError(f'{field} must be finite.')
            output[field]=float(value)
    for field in ('tire_temps','tire_wear'):
        if field in sample:
            values=sample[field]
            if not isinstance(values,dict):raise ValueError(f'{field} must be an object.')
            limit=(0,100) if field=='tire_wear' else (0,200)
            if any(k not in ('FL','FR','RL','RR') or not isinstance(v,(float,int)) or not math.isfinite(v) or not limit[0]<=v<=limit[1] for k,v in values.items()):raise ValueError(f'Invalid {field}.')
            output[field]=values.copy()
    return output

class Recording:
    def __init__(self,samples,provenance=None):
        if not isinstance(samples,list) or not 2<=len(samples)<=100000:raise ValueError('Recording needs 2–100,000 samples.')
        if provenance is not None and not isinstance(provenance,dict):raise ValueError('Recording provenance must be an object.')
        self.samples=[validate_sample(s) for s in samples]
        self.provenance=provenance or {'mode':'imported','source':'User supplied; unverified'}
        self.time=np.array([s['timestamp'] for s in self.samples]);self.distance=np.array([s['distance'] for s in self.samples])
        if (np.diff(self.time)<=0).any() or (np.diff(self.distance)<=0).any():raise ValueError('Single-lap timestamps and distances must strictly increase.')
        # Recorded values are lap-relative. Keep source start time only as provenance.
        offset=self.time[0];self.time-=offset
        for s in self.samples:s['timestamp']-=float(offset)
        self.columns={f:np.array([s[f] for s in self.samples]) for f in FIELDS if f not in ('timestamp','distance')}
        for f in ('x','y'):
            if all(f in s for s in self.samples):self.columns[f]=np.array([s[f] for s in self.samples])
        self.tyres={}
        for field in ('tire_temps','tire_wear'):
            self.tyres[field]={wheel:np.array([s[field][wheel] for s in self.samples]) for wheel in ('FL','FR','RL','RR') if all(wheel in s.get(field,{}) for s in self.samples)}
        brakes=self.columns['brake'];indices=np.flatnonzero((brakes[1:]>.3)&(brakes[:-1]<=.3))+1
        self.braking=np.array([self.distance[i-1]+(.3-brakes[i-1])/(brakes[i]-brakes[i-1])*(self.distance[i]-self.distance[i-1]) for i in indices])
    def interpolate(self,axis,value):
        if not math.isfinite(value) or not axis[0]<=value<=axis[-1]:raise ValueError('Sample outside reference range.')
        
        # Use searchsorted for O(log N) index lookup instead of O(N) linear interp search
        idx = np.searchsorted(axis, value, side='left')
        
        # Manual linear interpolation for basic fields to avoid repeated array scans in np.interp
        def get_val(vals, i):
            if i <= 0: return float(vals[0])
            if i >= len(vals): return float(vals[-1])
            # Local linear interpolation: y = y0 + (x - x0) * (y1 - y0) / (x1 - x0)
            x0, x1 = axis[i-1], axis[i]
            y0, y1 = vals[i-1], vals[i]
            return float(y0 + (value - x0) * (y1 - y0) / (x1 - x0))

        result={'timestamp':get_val(self.time, idx),'distance':get_val(self.distance, idx)}
        for field,values in self.columns.items():
            if field!='gear':
                result[field]=get_val(values, idx)
            else:
                result[field]=int(values[max(0,idx-1)])
        
        for field,wheels in self.tyres.items():
            if wheels:
                result[field]={wheel:get_val(values, idx) for wheel,values in wheels.items()}
        return result
    def at_distance(self,value):return self.interpolate(self.distance,value)
    def at_time(self,value):return self.interpolate(self.time,value)
    def payload(self):return {'schema_version':1,'provenance':self.provenance,'samples':self.samples}

class SessionAnalysis:
    PRIORITY={'LOW':1,'MEDIUM':2,'HIGH':3,'CRITICAL':4}
    def __init__(self,reference,recording=None):self.reference=reference;self.recording=recording;self.reset()
    def reset(self):self.previous=None;self.cooldowns=OrderedDict();self.last_braking=None
    def process(self,sample):
        sample=validate_sample(sample)
        if self.previous and (sample['timestamp']<=self.previous['timestamp'] or sample['distance']<self.previous['distance']):raise ValueError('Frame time must increase; reset before replaying a lap.')
        ref=self.reference.at_distance(sample['distance']);offset=None;alerts=[]
        onset=None
        if self.previous and self.recording is not None:
            crossed=self.recording.braking[(self.recording.braking>self.previous['distance'])&(self.recording.braking<=sample['distance'])]
            if len(crossed):onset=float(crossed[-1])
        elif self.previous and self.previous['brake']<=.3 and sample['brake']>.3:
            onset=self.previous['distance']+(.3-self.previous['brake'])/(sample['brake']-self.previous['brake'])*(sample['distance']-self.previous['distance'])
        if onset is not None and len(self.reference.braking):
            self.last_braking=None
            target=float(self.reference.braking[np.abs(self.reference.braking-onset).argmin()])
            # Conservative association: nearby, mutual-nearest onsets when both
            # recordings exist. Unpaired applications are not another corner.
            paired=self.recording is None or float(self.recording.braking[np.abs(self.recording.braking-target).argmin()])==onset
            if abs(target-onset)<=100 and paired:
                offset=onset-target;self.last_braking=offset
                if abs(offset)>5:alerts.append({'type':'BRAKING_EARLY' if offset<0 else 'BRAKING_LATE','severity':'MEDIUM' if offset<0 else 'HIGH','corner':f'Braking zone {target:.0f} m','msg':f'Braking {abs(offset):.1f} m {"early" if offset<0 else "late"} versus reference.','offset_m':offset})
        speed_delta=sample['speed']-ref['speed']
        if speed_delta < -12:alerts.append({'type':'SPEED_DEFICIT','severity':'MEDIUM','corner':f'Distance zone {int(sample["distance"]//250)*250} m','msg':f'Speed {abs(speed_delta):.1f} km/h below reference; inspect entry and exit.'})
        if ref['throttle']>.5 and sample['throttle']<ref['throttle']-.25:alerts.append({'type':'THROTTLE_HESITATION','severity':'LOW','corner':f'Distance zone {int(sample["distance"]//250)*250} m','msg':'Throttle pickup below reference.'})
        emitted=[]
        for alert in sorted(alerts,key=lambda a:self.PRIORITY[a['severity']],reverse=True):
            key=(alert['type'],alert['corner']);previous=self.cooldowns.get(key);p=self.PRIORITY[alert['severity']]
            if not previous or sample['timestamp']-previous[0]>=5 or p>previous[1]:
                emitted.append(alert);self.cooldowns[key]=(sample['timestamp'],p);self.cooldowns.move_to_end(key)
        while len(self.cooldowns)>128:self.cooldowns.popitem(last=False)
        lateral=None
        if all(k in sample and k in ref for k in ('x','y')):
            d=sample['distance'];before=self.reference.at_distance(max(self.reference.distance[0],d-5));after=self.reference.at_distance(min(self.reference.distance[-1],d+5))
            dx=after['x']-before['x'];dy=after['y']-before['y'];length=math.hypot(dx,dy)
            if length:lateral=((sample['x']-ref['x'])*(-dy)+(sample['y']-ref['y'])*dx)/length
        self.previous=sample
        return {'reference':ref,'speed_delta':speed_delta,'time_delta':sample['timestamp']-ref['timestamp'],'braking_offset_m':self.last_braking,'lateral_offset':lateral,'alerts':emitted}
