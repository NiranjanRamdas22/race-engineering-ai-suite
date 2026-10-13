# PROJECT_DOMAINS.md
## 🏎️ Project Technical Deep-Dives

### [D1] F1 Telemetry Lab
- **Core Logic:** Aligns telemetry from different laps using a common distance axis.
- **Optimization:** Adaptive sampling to maintain resolution in corners.
- **Key Metric:** Delta-time calculation between driver X and reference lap Y.
- **AI Context:** Used for visual validation of driver performance.

### [D2] AI Race Engineer (Desktop)
- **Core Logic:** Event-driven coaching engine.
- **Implementation:** Telemetry stream $\rightarrow$ Rule-based trigger $\rightarrow$ LLM synthesis $\rightarrow$ TTS (Text-to-Speech).
- **Optimization:** `asyncio.Queue` for non-blocking radio updates.
- **AI Context:** Demonstrates real-time agentic behavior.

### [D3] AI Replay Engineer
- **Core Logic:** Comparison of recorded samples against a reference.
- **Optimization:** $O(\log N)$ binary search via `np.searchsorted` for distance lookups.
- **Key Metric:** Braking point offset (meters) and speed deficits.
- **AI Context:** Real-time feedback loop via WebSockets.

### [D4] Race Summariser
- **Core Logic:** Transform structured race data into narrative debriefs.
- **Implementation:** SQLite $\rightarrow$ Jinja2 Templates $\rightarrow$ LLM-enhanced summaries.
- **Output:** Markdown reports with validated event timelines.
- **AI Context:** Summarization and structured-to-unstructured data conversion.

### [D5] Race Result Predictor
- **Core Logic:** GBDT (Gradient Boosting Decision Tree) for finishing position.
- **Optimization:** EWMA (Exponentially Weighted Moving Average) for driver/team form.
- **Probability:** Platt Scaling via Logistic Regression for Top-10 probabilities.
- **AI Context:** Predictive analytics and probability calibration.

### [D6] F1 Knowledge Assistant
- **Core Logic:** Hybrid RAG (Retrieval-Augmented Generation).
- **Implementation:** SQL (Numerical/Standings) + TF-IDF/Vector Search (Regulations).
- **Optimization:** SQLite FTS5 for instant entity resolution.
- **AI Context:** Domain-specific knowledge retrieval and synthesis.
