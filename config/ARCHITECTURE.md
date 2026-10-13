# Project Architecture: Motorsport Engineering Portfolio

This portfolio is a coordinated suite of six specialized Formula 1 engineering applications, managed by a central orchestration hub.

## 🏗️ System Overview

The project follows a **Hub-and-Spoke Architecture**. The `launcher.py` (the Hub) manages the lifecycle of six independent services (the Spokes).

### The Orchestration Hub (`launcher.py`)
The hub is a FastAPI application that provides:
- **Service Management:** Starts and stops backend processes using `subprocess`.
- **Health Monitoring:** Polls `/api/health` or `/_stcore/health` endpoints to verify service readiness.
- **Process Registry:** Maintains `.runtime/processes.json` to track PIDs and creation times, ensuring that only processes owned by the current session are terminated during shutdown.
- **Unified Routing:** Acts as a reverse proxy/redirector for the user to access the various demos from a single port (5501).

---

## 🏎️ The Service Map

| Service | Tech Stack | Port | Primary Purpose | Key Dependency |
| :--- | :--- | :--- | :--- | :--- |
| **Portfolio Hub** | FastAPI | 5501 | Central Navigation & Orchestration | `httpx`, `psutil` |
| **Race Summariser** | FastAPI | 8000 | Race debriefs & Markdown reports | `SQLite` |
| **Replay Engineer** | FastAPI | 8001 | Lap-by-lap coaching & delta analysis | `Ollama`, `numpy` |
| **Knowledge Assistant**| FastAPI | 8002 | RAG-based F1 regulation retrieval | `SQLite`, `scikit-learn`|
| **Result Predictor** | Streamlit | 8501 | ML Position & Probability prediction | `scikit-learn`, `joblib` |
| **Telemetry Lab** | Streamlit | 8502 | High-res lap trace & stint analysis | `FastF1`, `plotly` |
| **Race Engineer** | Tkinter | N/A | Real-time simulated radio coaching | `comtypes` (Windows) |

---

## 📊 Data Flow & Pipeline

### 1. Data Acquisition
The system primarily relies on the `FastF1` library to pull official Formula 1 timing and telemetry data.
- **Caching:** Data is cached locally in the `f1_cache` directory to prevent redundant API calls and speed up load times.

### 2. Processing Layers
- **Telemetry Analysis:** Raw samples $\rightarrow$ Distance-based interpolation $\rightarrow$ Corner-specific deltas.
- **ML Prediction:** Historical race data $\rightarrow$ Feature engineering (Rolling Means) $\rightarrow$ GBDT Model $\rightarrow$ Platt Scaling (Calibration).
- **Knowledge Retrieval:** User Query $\rightarrow$ TF-IDF Vectorization $\rightarrow$ Cosine Similarity $\rightarrow$ LLM Synthesis.

### 3. Frontend Presentation
- **Web-based:** Services use FastAPI (JSON) or Streamlit (Interactive Dashboards) delivered via HTTP.
- **Desktop-based:** The Race Engineer uses a Tkinter event loop for low-latency UI updates.

---

## ⚙️ Lifecycle Management

### Startup Sequence
1. `SETUP_PORTFOLIO.bat` $\rightarrow$ Initializes `.venv` and installs `requirements.txt`.
2. `START_PORTFOLIO.bat` $\rightarrow$ Executes `launcher.py`.
3. `launcher.py` $\rightarrow$ Iterates through `SERVICES` map $\rightarrow$ Checks Port $\rightarrow$ Spawns Process $\rightarrow$ Waits for Health Check $\rightarrow$ Opens Browser.

### Shutdown Sequence
1. `launcher.py stop` $\rightarrow$ Reads `.runtime/processes.json`.
2. Verifies PID ownership (to avoid killing unrelated system processes).
3. Sends `SIGTERM` $\rightarrow$ `SIGKILL` (if necessary).
4. Clears the registry.
