from pathlib import Path
import sys,asyncio
sys.path.insert(0,str(Path(__file__).parent))
import httpx
from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from typing import Literal
from database import F1Database
from retriever import F1Retriever
app=FastAPI(title='F1 Knowledge Assistant',version='3.0');db=F1Database();retriever=F1Retriever();semaphore=asyncio.Semaphore(1)
class QueryRequest(BaseModel):
    text:str=Field(min_length=2,max_length=1500)
    model_override:Literal['rules','llama3','mistral']='rules'
@app.get('/api/health')
async def health():return {'status':'ready'}
@app.get('/api/stats')
async def stats():return db.coverage()
@app.get('/api/suggestions')
async def suggestions():return [{'label':q} for q in ['Who won the 2025 Drivers championship?','Who won Monaco in 2024?','How many points did Ferrari score in 2023?','Compare Hamilton and Russell teammate qualifying in 2024','What are Silverstone circuit characteristics?','How does active aero work in 2026?','Explain 2026 MGU-K power limits','What are the 2026 tyre compound rules?']]
@app.post('/api/ask')
async def ask(req:QueryRequest):
    result=db.query_driver_or_season(req.text)
    if result is not None:return {'query':req.text,'engine_used':'Deterministic SQLite query','fallback_reason':None,**result}
    contexts=retriever.retrieve_context(req.text)
    if not contexts:return {'query':req.text,'engine_used':'Coverage check','fallback_reason':'No relevant supported dataset or document','answer':'Data unavailable: this question is outside the loaded numeric datasets and versioned regulation topics. Check coverage or ask a listed question.','sources':[],'available':False,'route_type':'DATA_UNAVAILABLE'}
    answer='\n\n'.join(d['text']+f"\nSeason {d['season']} • issue {d['issue']} ({d['issue_date']}) • {d['section']}" for d in contexts);engine='Versioned document retrieval';reason='Deterministic retrieval selected';generated=False
    if req.model_override!='rules':
        if semaphore.locked():raise HTTPException(429,'An explanation is already generating. Retry after it finishes.')
        async with semaphore:
            try:
                async with httpx.AsyncClient(timeout=4) as client:
                    r=await client.post('http://127.0.0.1:11434/api/generate',json={'model':req.model_override,'prompt':'Explain the question using only these supplied source summaries; do not invent details. Clearly state limitations. Question: '+req.text+'\nSources: '+answer,'stream':False,'options':{'num_predict':350}})
                    r.raise_for_status();text=r.json().get('response','').strip()
                    if len(text)>20:answer=text;engine='Ollama '+req.model_override;reason=None;generated=True
                    else:reason='AI returned no usable explanation'
            except (httpx.HTTPError,ValueError):reason='Local AI unavailable or timed out'
    return {'query':req.text,'answer':answer,'engine_used':engine,'fallback_reason':reason,'generated_explanation':generated,'available':True,'route_type':'DOCUMENT_RETRIEVAL','sources':[{'label':d['title']+f" • {d['section']} • issue {d['issue']}",'url':d['source_url'],'issue_date':d['issue_date'],'season':d['season'],'retrieved_at':d['retrieved_at']} for d in contexts],'retrieval_similarity':[d['retrieval_similarity'] for d in contexts]}
app.mount('/',StaticFiles(directory=Path(__file__).parents[1]/'frontend',html=True),name='frontend')
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8002)
