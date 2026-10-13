"""Export two cached official FastF1 laps as single-lap replay recordings."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'projects/f1-telemetry-analysis'));sys.path.insert(0,str(ROOT))
import fastf1,pandas as pd
from analytics import valid_laps,align_laps,corner_comparison
from motorsport.recorded import Recording
cache=ROOT/'projects/f1-telemetry-analysis/f1_cache';cache.mkdir(exist_ok=True);fastf1.Cache.enable_cache(str(cache))
s=fastf1.get_session(2024,'Silverstone','Q');s.load();laps=[];telemetry=[]
for driver in ('VER','HAM'):
    lap=valid_laps(s.laps.pick_drivers(driver)).iloc[0];tel=lap.get_telemetry().add_distance();laps.append(lap);telemetry.append(tel)
    tel=tel[tel.Distance>=0].sort_values('Distance').drop_duplicates('Distance');tel=tel[tel.Time.notna()]
    samples=[]
    for _,r in tel.iterrows():
        sample={'timestamp':float(r.Time.total_seconds()),'distance':float(r.Distance),'speed':float(r.Speed),'throttle':float(r.Throttle/100),'brake':float(r.Brake),'gear':int(r.nGear)}
        if pd.notna(r.X) and pd.notna(r.Y):sample.update(x=float(r.X),y=float(r.Y))
        if sample['timestamp']>=0:samples.append(sample)
    recording=Recording(samples,{'mode':'recorded official session','source':f'FastF1 2024 British Grand Prix qualifying â€¢ {driver} lap {int(lap.LapNumber)}','source_url':'https://docs.fastf1.dev/','position_units':'FastF1 source units (decimetres)','driver':driver,'lap':int(lap.LapNumber)})
    (ROOT/f'data/recordings/silverstone-2024-{driver.lower()}.json').write_text(json.dumps(recording.payload(),indent=2))
aligned=align_laps(*telemetry);c=s.get_circuit_info();c.add_marker_distance(laps[0]);corners=corner_comparison(aligned,c.corners)
report={'session':'2024 Silverstone Q','drivers':['VER','HAM'],'laps':[int(l.LapNumber) for l in laps],'samples':[len(t) for t in telemetry],'corners':len(corners),'corner_labels':corners.Corner.tolist(),'overlap_m':[float(aligned.Distance.min()),float(aligned.Distance.max())],'delta_end_s':float(aligned.Delta.iloc[-1]),'official_lap_delta_s':float((laps[0].LapTime-laps[1].LapTime).total_seconds()),'analysis_completed':True}
(ROOT/'.implementation/telemetry-live.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
