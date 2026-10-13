# PROJECT_MANIFEST.md
## 🎯 System Identity
- **Project Name:** Motorsport Engineering Portfolio
- **Domain:** Formula 1 Data Engineering & AI Analysis
- **Core Objective:** Demonstrating a full-stack pipeline from raw telemetry ingestion to ML-driven race prediction and RAG-based knowledge retrieval.

## 🗺️ Structural Map (Source of Truth)
```yaml
Root: "C:\Users\niran\Desktop\PORTFOLIO builds"
Directories:
  /src:
    /projects: { "ai-race-engineer": "Tkinter/AI Radio", "ai-replay-engineer": "FastAPI/WebSocket", "f1-knowledge-chatbot": "RAG/SQL", "f1-telemetry-analysis": "Streamlit/FastF1", "race-result-predictor": "ML/GBDT", "race-summariser": "FastAPI/LLM" }
    /data: { "raw": "Jolpica/FastF1", "processed": "Cleaned CSVs", "recordings": "Sample Laps" }
    /docs: "HTML User Guides"
    /scripts: "Build/Maintenance Tools"
    /tests: "Unit/Soak/Integration Tests"
    /.implementation: "Dev Logs/Snapshots"
    /.runtime: "Process Registry/Logs"
  /config: { "deps": "requirements.txt", "arch": "ARCHITECTURE.md" }
  /project_brain: "AI-Optimized Knowledge Base"
  /deploy: "Infrastructure as Code"
EntryPoints: [ "launcher.py", "index.html", "START_PORTFOLIO.bat" ]
```

## 🛠️ Global Tech Stack
- **Languages:** Python 3.14, JavaScript (Node.js for frontend tests)
- **Frameworks:** FastAPI (Backend), Streamlit (Dashboards), Tkinter (Desktop)
- **ML/Data:** Scikit-Learn (GBDT), Pandas, NumPy, FastF1, SQLite (FTS5)
- **LLM Integration:** OpenAI GPT-4o, Ollama (Llama3/Mistral)
- **Orchestration:** Custom Process Manager (`launcher.py`) with PID tracking.

## 📈 Data Lifecycle
1. **Ingestion:** `F1DataPipeline` $\rightarrow$ Jolpica API $\rightarrow$ Local Disk Cache.
2. **Splitting:** 2018–2023 (Train) $\rightarrow$ 2024 (Calibrate) $\rightarrow$ 2025 (Hold-out Test).
3. **Processing:** Distance-based interpolation $\rightarrow$ EWMA form weighting $\rightarrow$ Platt Scaling.
4. **Output:**- Numerical: Predictions/Deltas.
- Textual: AI-generated radio/summaries.
- Visual: Plotly interactive traces.
