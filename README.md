# F1 GRIDLAB

**Telemetry · Race Analytics · AI**

A collection of six applications for analysing Formula 1 telemetry, replaying recorded laps, generating race reports, exploring historical predictions, and answering questions from sourced data. This portfolio demonstrates the application of software engineering and computer science domains to motorsport analytics.

## Start

On Windows with Python 3.14 installed, open `SETUP_PORTFOLIO.bat`, then `START_PORTFOLIO.bat`. Setup installs the tested dependencies in `.venv`. The launcher opens the portfolio at `http://127.0.0.1:5501` and checks the five web services; the desktop demo starts from its card.

```powershell
.venv\Scripts\python.exe launcher.py status
.venv\Scripts\python.exe launcher.py stop
```

See [local setup and recording/import contracts](src/docs/setup.html), [validation & methodology](src/docs/validation.html), [engineering coverage](src/docs/engineering.html), and the six case studies linked from the portfolio. Read HTML guides through the launcher for working navigation and images.

## Projects

| Project | Demonstration |
| --- | --- |
| F1 Telemetry Lab | Official lap traces, metadata-labelled corners, track map and observed stint pace |
| AI Race Engineer | Telemetry simulation, recorded playback, reference guidance and optional Windows speech |
| AI Replay Engineer | Timestamp replay, measured braking offsets, cumulative delta and optional browser speech |
| Race Summariser | Source-backed race examples, persistent validated imports and Markdown export |
| Race Result Predictor | Full-grid historical scores, measured baselines and separate strategy scenarios |
| F1 Knowledge Assistant | Statistical race/qualifying comparisons and versioned document retrieval |

## Evidence and limits

Historical coverage is 2018–2025: 173 races, 3,458 classified entries. Training uses 2018–2023, selection/calibration uses 2024, and 2025 is held out. The model does **not** beat the simple baselines: position MAE 3.388 vs 3.338; probability Brier 0.1743 vs 0.1676 (lower is better).

The default replay and desktop simulator are labelled illustrative. Two sourced Silverstone qualifying recordings are in `src/data/recordings`. The chatbot covers four versioned 2026 regulation summaries and three circuit-characteristic profiles; unsupported questions are handled by returning a data-unavailable response. Live game UDP and public deployment remain deferred.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s src/tests -v
node src/tests/test_frontend.cjs
.venv\Scripts\python.exe -B src/tests/soak.py
```

The last command requires the launcher's Replay Engineer service and runs for 30 real minutes. Local evidence and implementation decisions are retained in `src/.implementation`; startup logs are in `src/.runtime`. These generated folders, environments, downloaded caches, and local databases are excluded from Git. Databases are populated from the included source data at startup. Source refresh and training commands are in the setup guide. Load only trusted local model artifacts.
