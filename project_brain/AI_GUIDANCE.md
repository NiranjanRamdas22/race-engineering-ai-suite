# AI_GUIDANCE.md
## 🤖 AI Interaction Protocol

This document provides the necessary context and constraints for any AI agent attempting to maintain, extend, or debug this project.

### 1. Core Constraints
- **Execution Environment:** Windows 10/11, Python 3.14.
- **Dependency Management:** Always use the `.venv` located at the root.
- **Port Management:** Do not change ports in `launcher.py` without updating the corresponding frontend links in `index.html`.
- **Data Integrity:** Do not modify the `data/` folder unless implementing a new data pipeline; the ML models are calibrated specifically to the 2018-2025 split.

### 2. Development Workflows
- **Adding a New Project:**
    1. Create folder in `/src/projects`.
    2. Add service definition to `launcher.py` (Title, Port, Health Endpoint, CWD).
    3. Add a link to the Hub (`index.html`).
- **Updating ML Models:**
    1. Modify `model_trainer.py` $\rightarrow$ Run `train_models.py` $\rightarrow$ Verify against `tests/`.
- **Debugging:**
    1. Check `.runtime/[service].log` for stderr.
    2. Use `launcher.py status` to verify service health.

### 3. Knowledge Retrieval Path
When asked about the project, the AI should resolve queries in this order:
1. **`PROJECT_MANIFEST.md`** $\rightarrow$ For high-level structure and "where is X?".
2. **`PROJECT_DOMAINS.md`** $\rightarrow$ For "how does X work?" or "what is the logic of Y?".
3. **`config/ARCHITECTURE.md`** $\rightarrow$ For system-wide data flow and orchestration.
4. **Source Code** $\rightarrow$ For implementation details.

### 4. Token-Efficient Summary (Compressed Context)
`Hub(launcher.py) -> Spokes(6 Apps) | Data(FastF1/Jolpica) -> ML(GBDT/EWMA) & RAG(SQL/FTS5) | UI(FastAPI/Streamlit/Tkinter) | Env(Win/Py3.14/venv)`
