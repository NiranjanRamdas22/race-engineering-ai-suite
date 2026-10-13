"""One local launcher with readiness checks and ownership-aware shutdown."""
from pathlib import Path
import sys,socket,subprocess,time,json,asyncio,os
import httpx,psutil
from fastapi import FastAPI,HTTPException,Request
from fastapi.responses import FileResponse,RedirectResponse,HTMLResponse
from fastapi.staticfiles import StaticFiles
ROOT=Path(__file__).resolve().parent;RUNTIME=ROOT/'src' / '.runtime';RUNTIME.mkdir(exist_ok=True)
PYTHON=sys.executable
SERVICES={
 'summariser':{'title':'Race Summariser','port':8000,'health':'/api/health','cwd':ROOT/'src/projects/race-summariser/race_summariser/backend','args':['-m','uvicorn','main:app','--host','127.0.0.1','--port','8000','--no-access-log']},
 'replay':{'title':'AI Replay Engineer','port':8001,'health':'/api/health','cwd':ROOT/'src/projects/ai-replay-engineer/ai_replay_engineer','args':['-m','uvicorn','server:app','--host','127.0.0.1','--port','8001','--no-access-log']},
 'chatbot':{'title':'F1 Knowledge Assistant','port':8002,'health':'/api/health','cwd':ROOT/'src/projects/f1-knowledge-chatbot/f1_knowledge_chatbot','args':['-m','uvicorn','main:app','--host','127.0.0.1','--port','8002','--no-access-log']},
 'predictor':{'title':'Race Result Predictor','port':8501,'health':'/_stcore/health','cwd':ROOT/'src/projects/race-result-predictor/race_result_predictor','args':['-m','streamlit','run',str(ROOT/'src/projects/race-result-predictor/race_result_predictor/app.py'),'--server.port','8501','--server.address','127.0.0.1','--server.headless','true','--browser.gatherUsageStats','false']},
 'telemetry':{'title':'F1 Telemetry Lab','port':8502,'health':'/_stcore/health','cwd':ROOT/'src/projects/f1-telemetry-analysis','args':['-m','streamlit','run',str(ROOT/'src/projects/f1-telemetry-analysis/app.py'),'--server.port','8502','--server.address','127.0.0.1','--server.headless','true','--browser.gatherUsageStats','false']},
 'portfolio':{'title':'Motorsport Portfolio','port':5501,'health':'/api/health','cwd':ROOT,'args':['-m','uvicorn','launcher:hub','--host','127.0.0.1','--port','5501','--no-access-log']}}
def occupied(port):
    with socket.socket() as s:s.settimeout(.2);return s.connect_ex(('127.0.0.1',port))==0

def ready(service):
    try:return httpx.get(f'http://127.0.0.1:{service["port"]}{service["health"]}',timeout=1).status_code==200
    except httpx.HTTPError:return False

def registry():
    path=RUNTIME/'processes.json'
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}
def remember(name,process):
    data=registry();data[name]={'pid':process.pid,'created':psutil.Process(process.pid).create_time()};(RUNTIME/'processes.json').write_text(json.dumps(data,indent=2))
def start_service(name,service):
    if occupied(service['port']):
        if ready(service):return 'already ready'
        raise RuntimeError(f"{service['title']}: port {service['port']} is occupied by an unready or different service. Close that service, then retry. Nothing was terminated.")
    log=(RUNTIME/(name+'.log')).open('w',encoding='utf-8')
    env={**os.environ,'PYTHONPATH':str(ROOT),'PYTHONUTF8':'1'}
    try:process=subprocess.Popen([PYTHON,'-B',*service['args']],cwd=service['cwd'],stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    finally:log.close()
    remember(name,process)
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        if ready(service):return 'ready'
        if process.poll() is not None:break
        time.sleep(.3)
    raise RuntimeError(f"{service['title']} did not become ready. See .runtime/{name}.log; install requirements.txt and retry.")
def desktop_running():
    item=registry().get('desktop')
    if not item:return False
    try:p=psutil.Process(item['pid']);return abs(p.create_time()-item['created'])<.1 and p.is_running()
    except psutil.Error:return False

def start_desktop():
    if desktop_running():return 'already running'
    path=ROOT/'src/projects/ai-race-engineer/ai_race_engineer/gui_dashboard.py';log=(RUNTIME/'desktop.log').open('w',encoding='utf-8')
    try:p=subprocess.Popen([PYTHON,'-B',str(path)],cwd=path.parent,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONPATH':str(ROOT)},creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    finally:log.close()
    remember('desktop',p);time.sleep(.5)
    if p.poll() is not None:raise RuntimeError('Desktop startup failed; see .runtime/desktop.log.')
    return 'started'

def stop_owned():
    remaining={}
    for name,item in registry().items():
        try:
            p=psutil.Process(item['pid'])
            if abs(p.create_time()-item['created'])>.1:continue
            p.terminate()
            try:p.wait(5)
            except psutil.TimeoutExpired:p.kill()
        except psutil.NoSuchProcess:pass
        except psutil.Error:remaining[name]=item
    (RUNTIME/'processes.json').write_text(json.dumps(remaining,indent=2))

hub=FastAPI(title='Motorsport Portfolio')
@hub.get('/api/health')
async def health():return {'status':'ready','project':'portfolio'}
@hub.get('/api/services')
async def service_status():
    async with httpx.AsyncClient(timeout=1) as client:
        async def check(name,s):
            try:ok=(await client.get(f'http://127.0.0.1:{s["port"]}{s["health"]}')).status_code==200
            except httpx.HTTPError:ok=False
            return {'id':name,'title':s['title'],'ready':ok,'demo_url':'/demo/'+name}
        rows=await asyncio.gather(*(check(n,s) for n,s in SERVICES.items() if n!='portfolio'))
    return rows+[{'id':'desktop','title':'AI Race Engineer','ready':desktop_running(),'demo_url':None}]
@hub.post('/api/desktop/start')
async def desktop_start(request:Request):
    if request.client.host not in ('127.0.0.1','::1') or request.headers.get('origin') not in (None,'http://127.0.0.1:5501','http://localhost:5501'):raise HTTPException(403,'Local portfolio origin required')
    try:return {'status':await asyncio.to_thread(start_desktop)}
    except RuntimeError as exc:raise HTTPException(503,str(exc))
@hub.get('/demo/{project}')
async def demo(project:str):
    if project not in SERVICES or project=='portfolio':raise HTTPException(404,'Unknown project')
    s=SERVICES[project]
    if not await asyncio.to_thread(ready,s):return HTMLResponse('<h1>Demo offline</h1><p>Start the suite using the local launcher, then retry.</p><a href="/">Return to portfolio</a>',status_code=503)
    return RedirectResponse(f'http://127.0.0.1:{s["port"]}/')
@hub.get('/')
@hub.get('/index.html')
async def index():return FileResponse(ROOT/'index.html')
hub.mount('/assets',StaticFiles(directory=ROOT/'src/assets'),name='assets')
hub.mount('/docs',StaticFiles(directory=ROOT/'src/docs',html=True),name='docs')
hub.mount('/recordings',StaticFiles(directory=ROOT/'src/data/recordings'),name='recordings')
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','status'],default='start',nargs='?');parser.add_argument('--desktop',action='store_true');parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if args.action=='stop':stop_owned();print('Stopped only processes owned by this launcher.')
    elif args.action=='status':
        for name,s in SERVICES.items():print(s['title']+': '+('ready' if ready(s) else 'offline'))
    else:
        try:
            for name,s in SERVICES.items():print(s['title']+': '+start_service(name,s))
            if args.desktop:print('AI Race Engineer: '+start_desktop())
            print('Portfolio ready: http://127.0.0.1:5501')
            if not args.no_browser:
                import webbrowser
                webbrowser.open('http://127.0.0.1:5501')
        except RuntimeError as exc:print(str(exc),file=sys.stderr);sys.exit(1)
