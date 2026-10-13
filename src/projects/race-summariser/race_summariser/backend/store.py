"""Validated race records persisted in SQLite; unknown facts remain unknown."""
from pathlib import Path
import sqlite3,json
from contextlib import contextmanager
from datetime import date as Date
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator

EVENT_TYPES=['START','FLAG','WEATHER','STRATEGY','PIT_STOP','PIT_CYCLE_GAIN','ON_TRACK_OVERTAKE','RETIREMENT_INHERITANCE','PACE','FINISH','RETIREMENT','POSITION_CHANGE']
class Event(BaseModel):
    model_config=ConfigDict(extra='forbid')
    lap:int=Field(ge=0,le=500)
    type:Literal['START','FLAG','WEATHER','STRATEGY','PIT_STOP','PIT_CYCLE_GAIN','ON_TRACK_OVERTAKE','RETIREMENT_INHERITANCE','PACE','FINISH','RETIREMENT','POSITION_CHANGE']
    driver:str=Field(default='Unknown',max_length=200)
    title:str=Field(min_length=1,max_length=300)
    description:str=Field(default='',max_length=3000)
    source_url:str|None=None
class Result(BaseModel):
    model_config=ConfigDict(extra='forbid')
    driver:str=Field(min_length=1,max_length=200)
    team:str|None=Field(default=None,max_length=200)
    time:str|None=None
    grid:int|None=Field(default=None,ge=0,le=30)
    pos:int|None=Field(default=None,ge=1,le=30)
    points:float|None=Field(default=None,ge=0)
    gap:str|None=None
class Stints(BaseModel):
    driver:str=Field(min_length=1,max_length=200)
    stints:list[str]=Field(default_factory=list,max_length=15)
class Source(BaseModel):
    label:str=Field(min_length=1,max_length=300)
    url:str|None=None
    scope:str='Supplied race record; not independently verified'
class RaceRecord(BaseModel):
    model_config=ConfigDict(extra='forbid')
    race_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name:str=Field(min_length=1,max_length=200)
    circuit:str=Field(min_length=1,max_length=200)
    country:str|None=None
    date:Date|None=None
    laps:int|None=Field(default=None,ge=1,le=500)
    weather:str|None=Field(default=None,max_length=500)
    winner:Result|None=None
    podium:list[Result]=Field(default_factory=list,max_length=3)
    fastest_lap:dict|None=None
    driver_of_the_day:dict|None=None
    key_timeline:list[Event]=Field(default_factory=list,max_length=500)
    strategy_stints:list[Stints]=Field(default_factory=list,max_length=30)
    sources:list[Source]=Field(default_factory=list,max_length=30)
    incomplete:bool=True
    @model_validator(mode='after')
    def validate_complete(self):
        if self.laps and any(e.lap>self.laps for e in self.key_timeline):raise ValueError('Timeline lap exceeds race lap count.')
        if len({p.pos for p in self.podium if p.pos is not None})!=len([p for p in self.podium if p.pos is not None]):raise ValueError('Duplicate podium positions.')
        self.incomplete=not(self.winner and self.laps and self.date and len(self.podium)==3 and self.sources)
        return self
class RaceStore:
    def __init__(self,path):
        self.path=str(path)
        with self.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS races (race_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:yield db
        finally:db.close()
    def save(self,race):
        # JSON-safe encoding includes dates; only validated caller records or shipped fixtures.
        payload=json.dumps(race,default=str,ensure_ascii=False)
        with self.connect() as db:db.execute('INSERT OR REPLACE INTO races VALUES (?,?)',(race['race_id'],payload))
    def get(self,race_id):
        with self.connect() as db:row=db.execute('SELECT payload FROM races WHERE race_id=?',(race_id,)).fetchone()
        return json.loads(row[0]) if row else None
    def all(self):
        with self.connect() as db:rows=db.execute('SELECT payload FROM races ORDER BY race_id').fetchall()
        return [json.loads(r[0]) for r in rows]

