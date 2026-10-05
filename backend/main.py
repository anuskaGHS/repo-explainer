"""FastAPI application entry point and API route definitions."""

import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException

# Ensure project root is available in sys.path for direct module resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from backend.schemas import ExplainRequest, ExplainResponse
    from backend.repo_processor import (
        clone_repo,
        get_relevant_files,
        build_file_tree,
        read_files,
    )
    from backend.llm_service import explain_repo
except ImportError:
    from schemas import ExplainRequest, ExplainResponse
    from repo_processor import (
        clone_repo,
        get_relevant_files,
        build_file_tree,
        read_files,
    )
    from llm_service import explain_repo

app = FastAPI(
    title="Local GitHub Repository Code Explainer",
    description="Analyze and explain public GitHub repositories using local LLM inference.",
    version="1.0.0",
)


@app.get("/health", summary="Health check")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {"status": "ok"}


@app.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Clone, analyze, and explain a GitHub repository",
)
def explain_repository(request: ExplainRequest) -> ExplainResponse:
    """Clone a public GitHub repository, analyze relevant files, and generate an explanation.

    Runs as a standard synchronous function in a threadpool to avoid blocking
    the FastAPI async event loop during Git operations and LLM inference.
    """
    # 1. Clone and file processing step
    try:
        repo_path = clone_repo(request.repo_url)
        relevant_files = get_relevant_files(repo_path)
        file_tree = build_file_tree(repo_path, relevant_files)
        file_records = read_files(relevant_files, repo_path)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except RuntimeError as err:
        raise HTTPException(
            status_code=400,
            detail=f"Repository clone error: {err}",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the repository.",
        )

    # 2. LLM explanation generation step
    try:
        explanation = explain_repo(file_records, file_tree)
    except RuntimeError as err:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service error: {err}",
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the repository explanation.",
        )

    return ExplainResponse(
        repo_name=repo_path.name,
        files_found=len(file_records),
        explanation=explanation,
    )
