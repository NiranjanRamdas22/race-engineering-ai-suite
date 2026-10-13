"""Refresh the shipped race demonstrations from FastF1 plus concise FIA annotations."""
from pathlib import Path
import json,sys
import fastf1
ROOT=Path(__file__).resolve().parents[1]
fastf1.Cache.enable_cache(str(ROOT/'projects/f1-telemetry-analysis/f1_cache'))
records={}
events={
 'silverstone':[(1,'START','George Russell','Russell leads the start','Russell led Hamilton at the start.'),(27,'PIT_STOP','Max Verstappen','Intermediate change','Verstappen changed to intermediate tyres.'),(34,'RETIREMENT_INHERITANCE','George Russell','Russell retires','Russell retired; the remaining cars moved up the classification.'),(39,'PIT_CYCLE_GAIN','Lewis Hamilton','Slick-tyre lead change','Hamilton moved ahead of Norris through the final pit cycle.'),(48,'ON_TRACK_OVERTAKE','Max Verstappen','Verstappen passes Norris','Verstappen passed Norris for second.'),(52,'FINISH','Lewis Hamilton','Hamilton wins','Hamilton finished ahead of Verstappen and Norris.')],
 'monza':[(1,'ON_TRACK_OVERTAKE','Oscar Piastri','Piastri passes Norris','Piastri took the lead at the second chicane.'),(15,'PIT_CYCLE_GAIN','Lando Norris','Norris undercuts Leclerc','Norris moved ahead of Leclerc after their first stops.'),(39,'STRATEGY','Charles Leclerc','One stop versus two','Ferrari kept Leclerc on one stop while the McLarens stopped twice.'),(45,'ON_TRACK_OVERTAKE','Oscar Piastri','Piastri passes Sainz','Piastri passed Sainz for second.'),(53,'FINISH','Charles Leclerc','Leclerc wins','Leclerc finished ahead of Piastri and Norris.')],
 'monaco':[(1,'FLAG','Field','Opening-lap red flag','The race stopped after the Perez and Haas collision.'),(1,'STRATEGY','Field','Tyre change during stoppage','The leading cars changed compounds during the red flag.'),(2,'START','Charles Leclerc','Standing restart','Leclerc led the standing restart.'),(51,'PIT_STOP','Lewis Hamilton','Hamilton changes tyres','Hamilton stopped and retained seventh place.'),(78,'FINISH','Charles Leclerc','Leclerc wins','Leclerc finished ahead of Piastri and Sainz.')]
}
sources={
 'silverstone':'https://api.fia.com/news/f1-hamilton-takes-emotional-record-breaking-ninth-win-silverstone-ahead-verstappen-and-norris',
 'monza':'https://www.fia.com/news/f1-leclerc-wins-ahead-mclaren-duo-ferraris-one-stop-monza-gamble-pays',
 'monaco':'https://www.fia.com/news/f1-leclerc-takes-emotional-home-win-monaco-ahead-piastri-and-sainz'}
for key,gp in [('silverstone','Silverstone'),('monza','Monza'),('monaco','Monaco')]:
    session=fastf1.get_session(2024,gp,'R');session.load(telemetry=False,weather=False,messages=False)
    result=session.results.sort_values('Position');podium=[];stints=[]
    for _,r in result.head(3).iterrows():
        time=str(r.Time).split('days ')[-1] if r.Time is not None else None
        podium.append({'pos':int(r.Position),'driver':r.FullName,'team':r.TeamName,'grid':int(r.GridPosition),'points':float(r.Points),'gap':'WINNER' if r.Position==1 else '+'+time})
        laps=session.laps.pick_drivers(r.Abbreviation)
        items=[]
        for _,group in laps.groupby('Stint'):
            compound=str(group.Compound.iloc[0]);items.append(f'{compound} (laps {int(group.LapNumber.min())}–{int(group.LapNumber.max())})')
        stints.append({'driver':r.FullName,'stints':items})
    race_id=key+'_2024';url=sources[key]
    records[race_id]={'race_id':race_id,'name':'2024 '+session.event.EventName,'circuit':{'silverstone':'Silverstone Circuit','monza':'Autodromo Nazionale Monza','monaco':'Circuit de Monaco'}[key],'country':session.event.Country,'date':str(session.date.date()),'laps':int(session.laps.LapNumber.max()),'winner':{'driver':podium[0]['driver'],'team':podium[0]['team'],'grid':podium[0]['grid']},'podium':podium,'strategy_stints':stints,'key_timeline':[{'lap':lap,'type':kind,'driver':driver,'title':title,'description':description,'source_url':url} for lap,kind,driver,title,description in events[key]],'sources':[{'label':'FIA race report','url':url,'scope':'Podium and concise selected race-event annotations, paraphrased; not an exhaustive timeline'},{'label':'FastF1 session timing','url':'https://docs.fastf1.dev/','scope':'Official timing feed via FastF1: classified podium, grid and lap/stint grouping; retrieved 2026-10-12'}],'incomplete':True}
    print(race_id,[(p['driver'],p['grid']) for p in podium],stints,flush=True)
(ROOT/'data/race-fixtures.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
