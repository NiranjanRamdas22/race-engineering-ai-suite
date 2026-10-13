"""Distance-based analytics; missing measurements stay unavailable."""
import numpy as np
import pandas as pd

def valid_laps(laps):
    out=laps.dropna(subset=['LapTime','LapNumber']).copy()
    for key in ('PitInTime','PitOutTime'):
        if key in out: out=out[out[key].isna()]
    if 'Deleted' in out: out=out[~out.Deleted.fillna(True).astype(bool)]
    if 'IsAccurate' in out: out=out[out.IsAccurate.fillna(False).astype(bool)]
    return out.sort_values('LapTime')

def seconds_delta(a,b):
    return None if a is pd.NaT or b is pd.NaT or pd.isna(a) or pd.isna(b) else float((a-b).total_seconds())

def clean_telemetry(tel):
    required=['Distance','Time','Speed','Throttle','Brake','nGear']
    missing=set(required)-set(tel.columns)
    if missing: raise ValueError('Unavailable telemetry channels: '+', '.join(sorted(missing)))
    out=pd.DataFrame(tel).copy()
    elapsed=pd.to_timedelta(out.Time).dt.total_seconds()
    out['Elapsed']=elapsed-elapsed.min()
    out=out.replace([np.inf,-np.inf],np.nan).dropna(subset=required+['Elapsed'])
    out=out.sort_values(['Distance','Elapsed']).drop_duplicates('Distance',keep='first')
    out['Brake']=out.Brake.astype(float)*100
    if len(out)<2: raise ValueError('At least two valid telemetry samples are required.')
    if (np.diff(out.Elapsed)<0).any(): raise ValueError('Time must increase with distance.')
    return out

def align_laps(tel1,tel2,samples=1000):
    a,b=clean_telemetry(tel1),clean_telemetry(tel2)
    start=max(a.Distance.min(),b.Distance.min());end=min(a.Distance.max(),b.Distance.max())
    if end<=start: raise ValueError('No overlapping telemetry distance range.')
    d=np.linspace(start,end,samples); result=pd.DataFrame({'Distance':d})
    for n,t in ((1,a),(2,b)):
        for source,target in [('Speed','Speed'),('Throttle','Throttle'),('Brake','Brake'),('nGear','Gear'),('Elapsed','Elapsed'),('X','X'),('Y','Y')]:
            if source in t:
                values=np.interp(d,t.Distance,t[source])
                result[f'{target}{n}']=np.rint(values) if target=='Gear' else values
    result['Delta']=result.Elapsed1-result.Elapsed2
    return result

def corner_comparison(aligned,corners):
    if corners is None or 'Distance' not in corners: return pd.DataFrame()
    markers=corners.sort_values('Distance').reset_index(drop=True);rows=[]
    for i,c in markers.iterrows():
        center=c.Distance;label=f"T{int(c.Number)}{str(c.get('Letter','') or '')}"
        lo=max(center-180,(markers.iloc[i-1].Distance+center)/2 if i else aligned.Distance.min())
        hi=min(center+180,(markers.iloc[i+1].Distance+center)/2 if i+1<len(markers) else aligned.Distance.max())
        window=aligned[(aligned.Distance>=lo)&(aligned.Distance<=hi)]
        row={'Corner':label,'Distance (m)':float(center),'Apex 1 (km/h)':None,'Apex 2 (km/h)':None,'Apex delta (km/h)':None,'Braking delta (m)':None,'Throttle pickup delta (m)':None}
        if pd.notna(center) and aligned.Distance.min()<=center<=aligned.Distance.max() and len(window)>=3:
            braking=[];pickup=[]
            for n in (1,2):
                apex=window[f'Speed{n}'].idxmin();ad=float(window.loc[apex,'Distance'])
                row[f'Apex {n} (km/h)']=float(window.loc[apex,f'Speed{n}'])
                before=aligned[(aligned.Distance>=lo-250)&(aligned.Distance<=ad)]
                on=(before[f'Brake{n}']>50)&(before[f'Brake{n}'].shift(1,fill_value=100)<=50)
                braking.append(float(before.loc[on,'Distance'].iloc[-1]) if on.any() else None)
                after=window[window.Distance>=ad]
                on=(after[f'Throttle{n}']>=90)&(after[f'Throttle{n}'].shift(1,fill_value=100)<90)
                pickup.append(float(after.loc[on,'Distance'].iloc[0]) if on.any() else None)
            row['Apex delta (km/h)']=row['Apex 1 (km/h)']-row['Apex 2 (km/h)']
            for key,v in [('Braking delta (m)',braking),('Throttle pickup delta (m)',pickup)]:
                if all(x is not None for x in v): row[key]=v[0]-v[1]
        rows.append(row)
    return pd.DataFrame(rows,dtype=object)

def degradation(laps):
    required={'LapTime','TyreLife','Stint','Compound'}
    if not required.issubset(laps.columns): return []
    out=laps.copy().dropna(subset=list(required));out=out[out.Compound.isin(['SOFT','MEDIUM','HARD'])]
    if 'Rainfall' in out: out=out[~out.Rainfall.fillna(True).astype(bool)]
    for key in ('PitInTime','PitOutTime'):
        if key in out: out=out[out[key].isna()]
    if 'IsAccurate' in out: out=out[out.IsAccurate.fillna(False).astype(bool)]
    if 'Deleted' in out: out=out[~out.Deleted.fillna(True).astype(bool)]
    if 'TrackStatus' in out: out=out[out.TrackStatus.astype(str)=='1']
    rows=[];keys=['Driver','Stint','Compound'] if 'Driver' in out else ['Stint','Compound']
    for group,stint in out.groupby(keys):
        stint=stint.sort_values('TyreLife').drop_duplicates('TyreLife')
        if len(stint)<5: continue
        x=stint.TyreLife.to_numpy(float);y=stint.LapTime.dt.total_seconds().to_numpy()
        slope,intercept=np.polyfit(x,y,1);variance=np.sum((y-(slope*x+intercept))**2)/(len(x)-2)
        uncertainty=1.96*np.sqrt(variance/np.sum((x-x.mean())**2))
        rows.append({'Stint':str(group),'Samples':len(x),'Pace slope (s/lap)':float(slope),'Approx. 95% ± (s/lap)':float(uncertainty)})
    return rows
