# Local GitHub Repository Code Explainer

An end-to-end local AI application that clones, analyzes, and explains public GitHub repositories using FastAPI, Streamlit, and local LLMs via Ollama.

---

## Quick Start for Evaluators

Follow these numbered steps in Windows PowerShell to set up and run the application locally.

### Prerequisites

Before beginning, ensure the following are installed on your machine:
- **Git** (available in your PowerShell PATH)
- **Python 3.10+**
- **Ollama** installed and running (`ollama serve` or the Ollama desktop app)

> **Important Notes:**
> - Ollama must be running before starting the backend.
> - The first run will take slightly longer as the model is loaded into memory / GPU VRAM.
> - For initial evaluation, **we strongly recommend testing with a small public repository (5 to 15 files)**, such as:
>   - `https://github.com/anuskaGHS/Python_Project`
>   - `https://github.com/octocat/Hello-World`
>   - `https://github.com/octocat/Spoon-Knife`

---

### Step-by-Step Setup (Windows PowerShell)

#### 1. Clone the Repository
```powershell
git clone https://github.com/anuskaGHS/repo-explainer
```

#### 2. Navigate into the Project Directory
```powershell
cd repo-explainer
```

#### 3. Create a Virtual Environment
```powershell
python -m venv venv
```

#### 4. Activate the Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(If PowerShell blocks script execution, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

#### 5. Install Dependencies
```powershell
pip install -r requirements.txt
```

#### 6. Pull the Local LLM Model in Ollama
```powershell
ollama pull llama3:8b
```

#### 7. Start the Backend API (Terminal 1)
In your activated virtual environment, start the FastAPI server:
```powershell
uvicorn backend.main:app
```
*(The API will be available at `http://127.0.0.1:8000` with interactive docs at `http://127.0.0.1:8000/docs`).*

#### 8. Start the Frontend UI (Terminal 2)
Open a second PowerShell terminal, navigate to `repo-explainer`, activate the virtual environment, and launch Streamlit:
```powershell
.\venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```

#### 9. Open the Application
Open your web browser and navigate to the Streamlit local URL:
```text
http://localhost:8501
```
Paste any public GitHub repository URL into the input field and click **"Analyze Repo"**.

---

## Architecture Flow

The system processes codebases locally from URL ingestion through synthesis to UI presentation:

```text
GitHub URL
    │
    ▼
[ Clone ] ───────── Clones the target public repo into a local directory using GitPython
    │
    ▼
[ Filter Files ] ── Filters out binaries, vendor dirs, lockfiles, and low-value assets;
    │               ranks source files by architectural importance (entry points, manifests, source code)
    │
    ▼
[ Local LLM ] ───── Generates concise symbol-aware summaries of prioritized files,
  (via Ollama)      then synthesizes a structured 4-part architectural explanation
    │
    ▼
[ FastAPI ] ─────── Exposes REST endpoints (`POST /explain`, `GET /health`) with strict Pydantic schemas
    │
    ▼
[ Streamlit ] ───── Renders an interactive interface with section cards, tech chips, and formatted code
```

### Detailed Pipeline
1. **GitHub URL**: The user submits a valid public repository clone URL in the Streamlit frontend.
2. **Clone (`repo_processor.py`)**: The repository is cloned into a workspace cache using GitPython.
3. **Filter & Priority Ranking (`repo_processor.py` & `llm_service.py`)**:
   - Skips media, binary assets, package lockfiles, tests, minified bundles, and vendor trees.
   - Extracts structured outlines (classes, functions, decorators) for files exceeding `MAX_FILE_CHARS`.
   - Ranks the most architecturally informative files up to `MAX_FILES`.
4. **Local LLM via Ollama (`llm_service.py`)**:
   - Queries Ollama locally without sending code to external third-party cloud APIs.
   - Summarizes top individual source files.
   - Produces a final cohesive breakdown with four clear sections: *Project Overview*, *What the project does*, *Main Technologies*, and *How it works*.
5. **FastAPI (`main.py`)**: Coordinates cloning, preprocessing, and LLM calls synchronously, returning structured responses with error handling.
6. **Streamlit (`frontend/app.py`)**: Displays the parsed explanation inside styled cards, rendering technologies exclusively as chips, formatting inline `<code>` blocks, and sanitizing untrusted inputs.

---

## Tech Stack

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Pydantic v2](https://docs.pydantic.dev/)
- **Repository Processing**: [GitPython](https://gitpython.readthedocs.io/)
- **Frontend**: [Streamlit](https://streamlit.io/), [Requests](https://requests.readthedocs.io/)
- **Local AI Engine**: [Ollama Python SDK](https://github.com/ollama/ollama-python) interfacing with a local Ollama daemon
- **Default LLM**: `llama3:8b` (Meta Llama 3 8B)

### Low RAM / Resource-Constrained Environments
If your machine has limited RAM/VRAM, you can easily switch to a smaller, lightweight model:
1. Pull the lighter model in Ollama:
   ```powershell
   ollama pull gemma3:1b
   ```
2. In `backend/llm_service.py`, update line 5:
   ```python
   MODEL_NAME = "gemma3:1b"
   ```
3. Restart the FastAPI server.

---

## Configurable Constants

All key pipeline limits and model parameters can be configured directly in `backend/llm_service.py`:

| Constant | Location | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `MODEL_NAME` | `backend/llm_service.py` | `"llama3:8b"` | Ollama model tag used for all file and repository generation calls. |
| `NUM_CTX` | `backend/llm_service.py` | `8192` | Context window size in tokens allocated for Ollama requests. |
| `MAX_FILES` | `backend/llm_service.py` | `15` | Maximum number of prioritized files selected for individual file summarization. |
| `MAX_FILE_CHARS` | `backend/llm_service.py` | `3000` | Character threshold for file content; files exceeding this length trigger outline compression (head characters + symbol outline). |
| `README_CHARS` | `backend/llm_service.py` | `6000` | Maximum character length of the root README included in the final synthesis prompt. |

Additional processing limits in `backend/repo_processor.py`:
- `MAX_SOURCE_FILE_BYTES` (`1_000_000` bytes): Maximum size threshold before dropping exceptionally large source files.
- `MAX_FILE_BYTES` (`100_000` bytes): Size limit applied to non-source configuration/markup files.

---

## Known Limitations

- **Public Repositories Only**: The application currently clones via standard HTTPS and does not authenticate with GitHub access tokens or SSH keys for private repositories.
- **Top 15 Files Summarized**: To ensure fast response times and fit within local context windows, only up to `MAX_FILES` (15) most architecturally relevant files are individually summarized. The remaining files are represented in the structural file tree.
- **Start-Plus-Outline Compression**: Very large source files are compressed down to their initial characters (`HEAD_CHARS = 1500`) plus regex-extracted symbol signatures (functions, classes, routes) rather than full source text.
- **Local Model Quality**: Small local models (e.g. 1B to 8B parameters) can occasionally miss subtle details, make inferences based on naming conventions, or misclassify secondary utilities compared to massive cloud models.
- **Inference Time on Large Codebases**: Running multi-step local inference across dozens of files on CPU or modest GPUs can take several minutes (up to ~10 minutes for substantial repositories).
