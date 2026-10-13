from pathlib import Path
import os
ROOT=Path(__file__).resolve().parents[1]
projects={
 'projects/f1-telemetry-analysis':('F1 Telemetry Lab','telemetry','app.py'),
 'projects/ai-race-engineer/ai_race_engineer':('AI Race Engineer','desktop','gui_dashboard.py'),
 'projects/ai-replay-engineer':('AI Replay Engineer','replay','ai_replay_engineer/server.py'),
 'projects/race-summariser/race_summariser':('Race Summariser','summariser','backend/main.py'),
 'projects/race-result-predictor/race_result_predictor':('Race Result Predictor','predictor','app.py'),
 'projects/f1-knowledge-chatbot':('F1 Knowledge Assistant','chatbot','f1_knowledge_chatbot/main.py')}
for path,(title,slug,entry) in projects.items():
    folder=ROOT/path;relative=Path(os.path.relpath(ROOT,folder)).as_posix()
    (folder/'README.md').write_text(f'# {title}\n\nUse the suite launcher from the repository root: `SETUP_PORTFOLIO.bat`, then `START_PORTFOLIO.bat`. All services have fixed documented ports and readiness checks.\n\n- [Reproducible setup and data contracts]({relative}/docs/setup.html)\n- [Capabilities, demonstration and limitations]({relative}/docs/{slug}.html)\n- [Measured validation]({relative}/docs/validation.html)\n\nActive entry point: `{entry}`. The suite defaults to deterministic local operation; optional voice and model services are labelled explicitly. Read the HTML guides through the local portfolio for working previews and navigation.\n',encoding='utf-8')
desktop=ROOT/'projects/ai-race-engineer/ai_race_engineer/setup.bat'
desktop.write_text('@echo off\ncd /d "%~dp0..\\..\\.."\ncall SETUP_PORTFOLIO.bat\n',encoding='utf-8')
# Keep direct project manifests compatible with the measured Plotly build.
for path in (ROOT/'projects').rglob('requirements.txt'):
    if 'venv' in path.parts:continue
    path.write_text(path.read_text().replace('plotly>=6,<7','plotly>=6,<8'),encoding='utf-8')
print('Updated six project guides and setup entry point')
