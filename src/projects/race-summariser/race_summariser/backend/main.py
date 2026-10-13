from pathlib import Path
import sys,json,asyncio
sys.path.insert(0,str(Path(__file__).parent))
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Literal
from race_data import RACES_DATABASE,generate_analytical_debrief
from store import RaceStore,RaceRecord,EVENT_TYPES
app=FastAPI(title='Race Summariser',version='3.0')
store=RaceStore(Path(__file__).parent/'races.sqlite3')
for race in RACES_DATABASE.values():
    existing=store.get(race['race_id'])
    if existing is None or any(s.get('label')=='Curated portfolio demonstration' for s in existing.get('sources',[])):
        store.save(race)
semaphore=asyncio.Semaphore(1)
class SummariseRequest(BaseModel):
    race_id:str
    model_override:Literal['rules','llama3','mistral']='rules'
@app.get('/api/health')
async def health():return {'status':'ready'}
@app.get('/api/taxonomy')
async def taxonomy():return EVENT_TYPES
@app.get('/api/races')
async def races():return [{'race_id':r['race_id'],'name':r['name'],'circuit':r['circuit'],'date':r.get('date'),'winner':(r.get('winner') or {}).get('driver'),'incomplete':r.get('incomplete',True)} for r in store.all()]
@app.get('/api/race/{race_id}')
async def details(race_id:str):
    race=store.get(race_id)
    if race is None:raise HTTPException(404,'Race not found')
    return race
@app.post('/api/ingest')
async def ingest(req:RaceRecord):
    record=req.model_dump(mode='json');store.save(record)
    return {'status':'ok','race_id':req.race_id,'incomplete':req.incomplete}
@app.post('/api/summarise')
async def summarise(req:SummariseRequest):
    race=await details(req.race_id);report=generate_analytical_debrief(race);engine='Facts-only template';reason='Deterministic engine selected';interpretation=False
    if req.model_override!='rules':
        if semaphore.locked():raise HTTPException(429,'A report is already generating. Retry when it finishes.')
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=4) as client:
                    response=await client.post('http://127.0.0.1:11434/api/generate',json={'model':req.model_override,'prompt':'Write an evidence-backed Markdown debrief using only these supplied facts. State missing data, label interpretation, include sources, do not invent podiums, causal claims or stints. Facts: '+json.dumps(race),'stream':False,'options':{'num_predict':1000}})
                    response.raise_for_status();text=response.json().get('response','').strip()
                    if len(text)>50:report=text;engine='Ollama '+req.model_override;reason=None;interpretation=True
                    else:reason='AI returned an incomplete report'
            except (httpx.HTTPError,ValueError):reason='Local AI unavailable or timed out'
    return {'race_id':req.race_id,'name':race['name'],'engine_used':engine,'fallback_reason':reason,'contains_generated_interpretation':interpretation,'report':report}
app.mount('/',StaticFiles(directory=Path(__file__).parents[1]/'frontend',html=True),name='frontend')
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8000)
