"""Jolpica's documented Ergast-compatible API with disk cache and pagination."""
from pathlib import Path
import json,time,hashlib
from datetime import datetime,timezone
import requests
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
class F1DataPipeline:
    def __init__(self,cache_dir=None):
        self.base_url='https://api.jolpi.ca/ergast/f1';self.cache_dir=Path(cache_dir or ROOT/'data/jolpica-cache');self.cache_dir.mkdir(parents=True,exist_ok=True)
        self.client=requests.Session();self.client.headers['User-Agent']='MotorsportPortfolio/3.0';self.last_request=0
    def fetch_json(self,endpoint,offset=0):
        url=f'{self.base_url}/{endpoint.strip("/")}/';key=hashlib.sha256(f'{url}?limit=100&offset={offset}'.encode()).hexdigest();path=self.cache_dir/(key+'.json')
        if path.exists():return json.loads(path.read_text(encoding='utf-8'))['response']
        wait=max(0,1.6-(time.monotonic()-self.last_request))
        if wait:time.sleep(wait)
        for attempt in range(3):
            self.last_request=time.monotonic();r=self.client.get(url,params={'limit':100,'offset':offset},timeout=(10,30))
            if r.status_code==429:
                time.sleep(min(60,float(r.headers.get('Retry-After','30'))));continue
            r.raise_for_status();data=r.json()
            if 'MRData' not in data:raise ValueError('Jolpica response lacks MRData.')
            path.write_text(json.dumps({'url':r.url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'response':data}),encoding='utf-8');return data
        raise RuntimeError('Jolpica rate limit persisted; cached downloads are preserved. Retry later.')
    def pages(self,endpoint):
        offset=0
        while True:
            data=self.fetch_json(endpoint,offset);yield data;mr=data['MRData'];limit=int(mr['limit']);total=int(mr['total'])
            if offset+limit>=total:break
            if limit<=0:raise ValueError('Invalid pagination limit.')
            offset+=limit
    def parse_races(self,data,kind):
        out=[]
        for race in data['MRData']['RaceTable']['Races']:
            season=int(race['season']);round_=int(race['round']);c=race['Circuit']
            for result in race.get(kind,[]):
                d=result['Driver'];constructor=result['Constructor']
                row={'season':season,'round':round_,'raceId':season*100+round_,'date':race.get('date'),'raceName':race['raceName'],'raceUrl':race.get('url'),'circuitId':c['circuitId'],'circuitName':c['circuitName'],'country':c['Location'].get('country'),'locality':c['Location'].get('locality'),'lat':c['Location'].get('lat'),'long':c['Location'].get('long'),'driverId':d['driverId'],'driverName':d['givenName']+' '+d['familyName'],'code':d.get('code'),'constructorId':constructor['constructorId'],'constructorName':constructor['name'],'source_url':f'{self.base_url}/{season}/{round_}/{"results" if kind=="Results" else "qualifying"}/'}
                if kind=='Results':row.update(position_res=int(result['position']),grid=int(result['grid']),points=float(result['points']),status=result['status'],laps=int(result.get('laps',0)))
                else:row.update(position_qual=int(result['position']),Q1=result.get('Q1'),Q2=result.get('Q2'),Q3=result.get('Q3'))
                out.append(row)
        return out
    def get_season_results(self,year):return pd.DataFrame([r for page in self.pages(f'{year}/results') for r in self.parse_races(page,'Results')])
    def get_season_qualifying(self,year):return pd.DataFrame([r for page in self.pages(f'{year}/qualifying') for r in self.parse_races(page,'QualifyingResults')])
    def build_dataset(self,start_year,end_year):
        rows=[]
        for year in range(start_year,end_year+1):
            print(f'Downloading historical {year}',flush=True)
            results=self.get_season_results(year);qual=self.get_season_qualifying(year)
            # Left join preserves all classified starters, including absent qualifying.
            merged=results.merge(qual[['raceId','driverId','position_qual','Q1','Q2','Q3']],on=['raceId','driverId'],how='left',validate='one_to_one')
            merged['qualifying_available']=merged.position_qual.notna()
            merged['position_qual']=merged.position_qual.fillna(merged.grid.where(merged.grid>0,20))
            rows.append(merged)
        return pd.concat(rows,ignore_index=True)
    def standings(self,year,kind):
        key='DriverStandings' if kind=='driver' else 'ConstructorStandings';endpoint=f'{year}/{kind}standings'
        lists=[s for page in self.pages(endpoint) for s in page['MRData']['StandingsTable']['StandingsLists']]
        return {'season':year,'round':int(lists[0]['round']) if lists else None,'source_url':f'{self.base_url}/{endpoint}/','rows':[r for s in lists for r in s[key]]}
if __name__=='__main__':
    p=F1DataPipeline();df=p.build_dataset(2018,2025);target=ROOT/'data';target.mkdir(exist_ok=True);df.to_csv(target/'historical.csv',index=False)
    df.to_json(target/'historical.json',orient='records',indent=2)
    standings={str(y):{k:p.standings(y,k) for k in ('driver','constructor')} for y in range(2018,2026)}
    (target/'standings.json').write_text(json.dumps(standings,indent=2),encoding='utf-8')
    coverage={'source':'Jolpica F1','source_url':p.base_url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'seasons':list(range(2018,2026)),'rows':len(df),'races':int(df.raceId.nunique()),'missing_qualifying':int((~df.qualifying_available).sum()),'season_races':df.groupby('season').raceId.nunique().to_dict()}
    (target/'coverage.json').write_text(json.dumps(coverage,indent=2),encoding='utf-8');print(json.dumps(coverage),flush=True)
