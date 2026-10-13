from pathlib import Path
import sys,csv,json,asyncio,uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from motorsport.recorded import Recording,SessionAnalysis
import httpx
from fastapi import FastAPI,WebSocket,WebSocketDisconnect,HTTPException
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).parent
with (ROOT/'reference_lap.csv').open() as f:
    rows=[{k:float(v) for k,v in r.items()} for r in csv.DictReader(f)]
reference=Recording(rows,{'mode':'illustrative simulation','source':'Locally generated Silverstone-like speed profile; not an official pole lap','position_units':None})
app=FastAPI(title='AI Replay Engineer',version='3.0')
@app.get('/api/health')
async def health():return {'status':'ready','mode':reference.provenance['mode']}
@app.get('/api/reference-lap')
async def reference_lap():return reference.payload()
@app.post('/api/validate-recording')
async def validate_recording(payload:dict):
    try:return Recording(payload.get('samples'),payload.get('provenance')).payload()
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))

async def coaching(alert,model):
    fallback=alert['msg'];reason='Rules selected'
    if model!='rules':
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response=await client.post('http://127.0.0.1:11434/api/generate',json={'model':model,'prompt':'One concise coaching sentence based only on this measured alert. Do not invent distances or strategy: '+fallback,'stream':False,'options':{'num_predict':80}})
                response.raise_for_status();answer=response.json().get('response','').strip()
                if answer:return answer,f'Ollama {model}',None
                reason='AI returned no usable text'
        except (httpx.HTTPError,ValueError):reason='Local AI unavailable or timed out'
    return fallback,'Rules',reason

@app.websocket('/ws/telemetry')
async def telemetry_socket(ws:WebSocket):
    await ws.accept();session_id=str(uuid.uuid4());seq=0;analysis=SessionAnalysis(reference);pending=None;model='rules';closed=False
    async def emit_coaching(alert,generation,number):
        text,engine,reason=await coaching(alert,model)
        if not closed and session_id==generation:
            await ws.send_json({'type':'COACHING','session_id':generation,'seq':number,'text':text,'severity':alert['severity'],'engine_used':engine,'fallback_reason':reason})
    try:
        while True:
            try:message=json.loads(await ws.receive_text())
            except json.JSONDecodeError:raise ValueError('Malformed JSON.')
            if not isinstance(message,dict):raise ValueError('Message must be an object.')
            kind=message.get('type')
            if kind in ('RESET','CONFIGURE'):
                sid=message.get('session_id')
                if not isinstance(sid,str) or not 1<=len(sid)<=80:raise ValueError('A session_id of 1–80 characters is required.')
                if pending:
                    pending.cancel();await asyncio.gather(pending,return_exceptions=True);pending=None
                session_id=sid;seq=0;analysis.reset()
                if kind=='CONFIGURE':
                    payload=message.get('reference')
                    if not isinstance(payload,dict):raise ValueError('Reference recording required.')
                    run_payload=message.get('recording')
                    recorded=Recording(run_payload.get('samples'),run_payload.get('provenance')) if isinstance(run_payload,dict) else None
                    analysis=SessionAnalysis(Recording(payload.get('samples'),payload.get('provenance')),recording=recorded)
                model=message.get('model','rules')
                if model not in ('rules','llama3','mistral'):raise ValueError('Unsupported coaching model.')
                await ws.send_json({'type':'RESET_ACK','session_id':session_id,'seq':0})
                continue
            if kind!='FRAME':raise ValueError('Use RESET, CONFIGURE or FRAME.')
            if message.get('session_id')!=session_id:continue
            number=message.get('seq')
            if isinstance(number,bool) or not isinstance(number,int) or number<=seq:raise ValueError('Sequence must increase.')
            result=analysis.process(message.get('sample'));seq=number
            await ws.send_json({'type':'FRAME_UPDATE','session_id':session_id,'seq':seq,**result})
            if result['alerts'] and (pending is None or pending.done()):
                pending=asyncio.create_task(emit_coaching(result['alerts'][0],session_id,seq))
    except WebSocketDisconnect:pass
    except (ValueError,TypeError,KeyError) as exc:
        await ws.send_json({'type':'ERROR','session_id':session_id,'seq':seq,'message':str(exc)});await ws.close(code=1008,reason='Invalid telemetry')
    finally:
        closed=True
        if pending:
            pending.cancel();await asyncio.gather(pending,return_exceptions=True)
app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True),name='frontend')
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8001)
