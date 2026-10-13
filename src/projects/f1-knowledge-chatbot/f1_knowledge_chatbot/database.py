"""Versioned SQLite knowledge, explicit query parsing and deterministic numeric answers."""
from pathlib import Path
from contextlib import contextmanager
import sqlite3,json,re,hashlib
from statistics import median
ROOT=Path(__file__).resolve().parents[3]

class F1Database:
    def __init__(self,db_path=None):
        self.db_path=str(db_path or Path(__file__).parent/'f1_knowledge.db');self.initialize()
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.db_path,timeout=10);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
    def initialize(self):
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS knowledge_meta (key TEXT PRIMARY KEY,value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS race_entries (season INTEGER,raceId INTEGER,driverId TEXT,constructorId TEXT,payload TEXT,PRIMARY KEY(raceId,driverId))')
            db.execute('CREATE TABLE IF NOT EXISTS season_standings (season INTEGER,kind TEXT,entityId TEXT,name TEXT,position INTEGER,points REAL,wins INTEGER,round INTEGER,complete INTEGER,source TEXT,PRIMARY KEY(season,kind,entityId))')
            db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY,payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS circuit_facts (id TEXT PRIMARY KEY,payload TEXT)')
            
            # Use contentless-delete tables or simple FTS5 tables. 
            # To avoid 'no such column: T.raceName' errors during MATCH, we define the columns explicitly.
            db.execute('DROP TABLE IF EXISTS entities_fts')
            db.execute('CREATE VIRTUAL TABLE entities_fts USING fts5(name, entityId, kind)')
            db.execute('DROP TABLE IF EXISTS races_fts')
            db.execute('CREATE VIRTUAL TABLE races_fts USING fts5(raceName, circuitId, circuitName)')
            
        files=[ROOT/'data'/name for name in ('historical.json','standings.json','coverage.json','regulations.json','circuit-characteristics.json')]
        fingerprint='|'.join(str(p.stat().st_mtime_ns) if p.exists() else 'missing' for p in files)
        with self.connect() as db:
            old=db.execute("SELECT value FROM knowledge_meta WHERE key='fingerprint'").fetchone()
            if old and old[0]==fingerprint:return
            if files[0].exists():
                rows=json.loads(files[0].read_text(encoding='utf-8'));db.execute('DELETE FROM race_entries')
                db.executemany('INSERT INTO race_entries VALUES (?,?,?,?,?)',[(r['season'],r['raceId'],r['driverId'],r['constructorId'],json.dumps(r,ensure_ascii=False)) for r in rows])
            coverage=json.loads(files[2].read_text()) if files[2].exists() else {}
            if files[1].exists():
                standings=json.loads(files[1].read_text());db.execute('DELETE FROM season_standings')
                for year,types in standings.items():
                    for kind,data in types.items():
                        complete=int(data['round']==coverage.get('season_races',{}).get(year))
                        for r in data['rows']:
                            entity=r['Driver' if kind=='driver' else 'Constructor'];identity=entity['driverId' if kind=='driver' else 'constructorId'];name=entity['givenName']+' '+entity['familyName'] if kind=='driver' else entity['name']
                            db.execute('INSERT INTO season_standings VALUES (?,?,?,?,?,?,?,?,?,?)',(int(year),kind,identity,name,int(r['position']),float(r['points']),int(r['wins']),data['round'],complete,data['source_url']))
            for file,table in [(files[3],'documents'),(files[4],'circuit_facts')]:
                if file.exists():
                    db.execute(f'DELETE FROM {table}')
                    for r in json.loads(file.read_text(encoding='utf-8')):db.execute(f'INSERT INTO {table} VALUES (?,?)',(r.get('id',r.get('circuitId')),json.dumps(r)))
            
            # Rebuild FTS indices
            db.execute('INSERT INTO entities_fts(name, entityId, kind) SELECT name, entityId, kind FROM season_standings')
            # Extract race data from JSON payload in race_entries for the FTS table
            # We use a temp table or a subquery to flatten the JSON payloads
            race_data=db.execute('SELECT payload FROM race_entries').fetchall()
            race_fts_rows=[]
            for r in race_data:
                p=json.loads(r[0])
                race_fts_rows.append((p['raceName'], p['circuitId'], p['circuitName']))
            db.executemany('INSERT INTO races_fts(raceName, circuitId, circuitName) VALUES (?,?,?)', race_fts_rows)
            
            db.execute("INSERT OR REPLACE INTO knowledge_meta VALUES ('fingerprint',?)",(fingerprint,))
            db.execute("INSERT OR REPLACE INTO knowledge_meta VALUES ('coverage',?)",(json.dumps(coverage),))
    def entries(self,season=None):
        with self.connect() as db:
            rows=db.execute('SELECT payload FROM race_entries WHERE season=?',(season,)).fetchall() if season is not None else db.execute('SELECT payload FROM race_entries').fetchall()
        return [json.loads(r[0]) for r in rows]
    def documents(self):
        with self.connect() as db:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM documents')]
    def coverage(self):
        with self.connect() as db:
            row=db.execute("SELECT value FROM knowledge_meta WHERE key='coverage'").fetchone();coverage=json.loads(row[0]) if row else {}
            coverage['regulation_documents']=db.execute('SELECT COUNT(*) FROM documents').fetchone()[0];coverage['circuit_characteristics']=db.execute('SELECT COUNT(*) FROM circuit_facts').fetchone()[0]
            coverage['standings']=[dict(r) for r in db.execute('SELECT DISTINCT season,round,complete FROM season_standings ORDER BY season')]
        return coverage
    def unavailable(self,detail):return {'answer':'Data unavailable: '+detail,'sources':[],'available':False,'route_type':'DATA_UNAVAILABLE'}
    def parse(self,query):
        q=query.lower();years=[int(x) for x in re.findall(r'\b(?:19|20)\d{2}\b',q)];drivers=[];teams=[];races=[]
        with self.connect() as db:
            entities=[dict(r) for r in db.execute('SELECT DISTINCT entityId,name,kind FROM season_standings')]
        def has(alias):return bool(re.search(r'(?<!\w)'+re.escape(alias.lower())+r'(?!\w)',q))
        for e in entities:
            aliases=[e['name'],e['entityId'].replace('_',' ')]
            if e['kind']=='driver':aliases.append(e['name'].split()[-1])
            if any(has(a) for a in aliases):
                target=drivers if e['kind']=='driver' else teams
                if e['entityId'] not in target:target.append(e['entityId'])
        named_races=[]
        for r in self.entries():
            if has(r['raceName']) or has(r['raceName'].replace(' Grand Prix','')):
                if r['raceName'] not in named_races:named_races.append(r['raceName'])
            aliases=[r['circuitId'].replace('_',' '),r['circuitName'],r['raceName'].replace(' Grand Prix','')]
            if r['circuitId']=='silverstone':aliases+=['silverstone','british']
            if r['circuitId']=='monza':aliases+=['monza','italian']
            if any(has(a) for a in aliases) and r['circuitId'] not in races:races.append(r['circuitId'])
        if 'red bull' in q and 'red_bull' not in teams:teams.append('red_bull')
        return {'text':q,'years':years,'year':years[0] if len(years)==1 else None,'drivers':drivers,'teams':teams,'races':races,'race_names':named_races}
    def query_driver_or_season(self,query):
        parsed=self.parse(query);q=parsed['text'];year=parsed['year'];drivers=parsed['drivers'];teams=parsed['teams'];races=parsed['races']
        numeric=any(k in q for k in ('champion','who won','winner','points','wins','qualifying','qualify','teammate','head-to-head','results','finish','standings','pole'))
        circuit=any(k in q for k in ('circuit','track','length','characteristic')) and races and not numeric
        if circuit:
            with self.connect() as db:row=db.execute('SELECT payload FROM circuit_facts WHERE id=?',(races[0],)).fetchone()
            if not row:return self.unavailable('Circuit characteristics not loaded for this circuit; location and race results are available.')
            c=json.loads(row[0]);return {'answer':f"{c['name']}: {c['length_km']} km. {c['characteristics']}\n{c['layout_scope']}",'sources':[{'label':'Formula 1 circuit guide','url':c['source_url']}],'available':True,'route_type':'CIRCUIT_FACTS'}
        if not numeric:return None
        seasons=self.coverage().get('seasons',[])
        if year is None:return self.unavailable('Specify one season year for numeric comparisons or race results.')
        if year not in seasons:return self.unavailable(f'{year} numeric data is outside loaded coverage ({min(seasons) if seasons else "none"}–{max(seasons) if seasons else "none"}).')
        entries=self.entries(year)
        if 'grand prix' in q and not races:return self.unavailable('The requested Grand Prix could not be identified in the loaded data.')
        if ('qual' in q and (len(drivers)>1 or 'teammate' in q or 'head-to-head' in q)):
            return self.teammate_comparison(year,drivers)
        if races:
            if len(races)>1:return self.unavailable('Specify one Grand Prix.')
            race=[r for r in entries if r['raceName'] in parsed['race_names']] if parsed['race_names'] else [r for r in entries if r['circuitId']==races[0]]
            if not race:return self.unavailable('This circuit did not have a loaded race in that season.')
            if len({r['raceId'] for r in race})!=1:return self.unavailable('This circuit hosted multiple Grands Prix that year. Specify the race name.')
            qualifying=any(k in q for k in ('qualifying','pole'))
            if drivers:
                selected=[r for r in race if r['driverId'] in drivers]
                if not selected:return self.unavailable('Requested driver absent from this race.')
            else:selected=sorted(race,key=lambda r:r['position_qual'] if qualifying else r['position_res'])[:1 if any(k in q for k in ('who won','winner','pole')) else 3]
            lines=[f"{year} {race[0]['raceName']} {'qualifying' if qualifying else 'race results'}:"]
            for r in selected:
                if qualifying and not r.get('qualifying_available'):return self.unavailable('Qualifying result missing; grid fallback is not a qualifying answer.')
                lines.append(f"- {r['driverName']} ({r['constructorName']}): P{int(r['position_qual'] if qualifying else r['position_res'])}"+(f" — {r['status']}" if not qualifying else ''))
            return {'answer':'\n'.join(lines),'sources':[{'label':race[0]['raceName']+' '+str(year),'url':race[0]['source_url'].replace('results/','qualifying/') if qualifying else race[0]['source_url']}],'available':True,'route_type':'SQL_STATISTICAL'}
        constructor='constructor' in q or ('team' in q and not drivers) or (teams and not drivers)
        if not drivers and not teams and 'championship' not in q and 'champion' not in q:
            return self.unavailable('Specify a supported Grand Prix, driver, constructor, or an explicit F1 championship question.')
        kind='constructor' if constructor else 'driver';identity=(teams or [None])[0] if constructor else (drivers or [None])[0]
        if len(drivers)>1:return self.unavailable('Multiple-driver season comparisons require an explicit teammate qualifying question.')
        with self.connect() as db:
            if identity:row=db.execute('SELECT * FROM season_standings WHERE season=? AND kind=? AND entityId=?',(year,kind,identity)).fetchone()
            elif any(k in q for k in ('champion','who won','winner')):row=db.execute('SELECT * FROM season_standings WHERE season=? AND kind=? AND position=1',(year,kind)).fetchone()
            else:return self.unavailable('Specify a driver or constructor for points/wins, or ask for the championship winner.')
        if not row:return self.unavailable('Requested entity has no standings record for this season.')
        r=dict(row);completed='Completed season' if r['complete'] else f"Partial snapshot after round {r['round']}"
        championship=any(k in q for k in ('champion','who won','winner')) and not identity
        if championship and not r['complete']:return self.unavailable('Only a partial standings snapshot is loaded; a champion cannot be inferred.')
        answer=f"{year} {r['name']}: P{r['position']}, {r['points']:g} points, {r['wins']} Grand Prix wins. {completed}."
        if championship:answer=f"{r['name']} won the {year} {'Constructors' if constructor else 'Drivers'} championship with {r['points']:g} points. {completed}."
        return {'answer':answer,'sources':[{'label':f'Jolpica {year} {kind} standings, round {r["round"]}','url':r['source']}],'available':True,'route_type':'SQL_STATISTICAL'}
    def teammate_comparison(self,year,drivers):
        if not 1<=len(drivers)<=2:return self.unavailable('Name one driver and their teammate, or two teammate drivers.')
        entries=self.entries(year);by_race={}
        for r in entries:by_race.setdefault(r['raceId'],[]).append(r)
        pairs=[];exclusions=[];wins={};deltas=[]
        def seconds(t):
            if not t:return None
            try:
                parts=t.split(':');v=float(parts[-1])+(float(parts[-2])*60 if len(parts)>1 else 0);return v if v>0 else None
            except (ValueError,AttributeError):return None
        for rid,race in sorted(by_race.items()):
            first=next((r for r in race if r['driverId']==drivers[0]),None)
            if not first:continue
            other=next((r for r in race if r['driverId']!=first['driverId'] and r['constructorId']==first['constructorId'] and (len(drivers)==1 or r['driverId']==drivers[1])),None)
            if not other:
                exclusions.append({'race':first['raceName'],'reason':'No matching teammate entry'});continue
            if any(not r.get('qualifying_available') or seconds(r.get('Q1')) is None for r in (first,other)):
                exclusions.append({'race':first['raceName'],'reason':'Incomplete qualifying; both drivers need a valid Q1 time'});continue
            winner=first if first['position_qual']<other['position_qual'] else other
            if first['position_qual']!=other['position_qual']:wins[winner['driverName']]=wins.get(winner['driverName'],0)+1
            phase=next((p for p in ('Q3','Q2','Q1') if seconds(first.get(p)) is not None and seconds(other.get(p)) is not None),'Q1')
            delta=seconds(first[phase])-seconds(other[phase]);deltas.append(delta)
            pairs.append({'race':first['raceName'],'round':first['round'],'drivers':[first['driverName'],other['driverName']],'qualifying_ranks':[first['position_qual'],other['position_qual']],'shared_phase':phase,'lap_time_delta_s':round(delta,3),'url':first['source_url'].replace('results/','qualifying/')})
        if not pairs:return self.unavailable('No paired complete teammate qualifying sessions for these drivers in this season.')
        answer=f"{year} teammate qualifying: {len(pairs)} paired sessions. Qualifying-rank wins: "+', '.join(f'{name} {n}' for name,n in wins.items())+f". Median first-driver minus teammate lap-time delta in their latest common phase: {median(deltas):+.3f} s. Excluded {len(exclusions)} sessions; both drivers must have valid Q1 data and the same constructor. Qualifying positions are classified qualifying ranks, not race grid penalties."
        return {'answer':answer,'available':True,'route_type':'SQL_COMPARISON','paired_sessions':len(pairs),'exclusions':exclusions,'source_sessions':pairs,'sources':[{'label':p['race']+f" round {p['round']}",'url':p['url']} for p in pairs]}
