"""Test script to verify end-to-end repository cloning, processing, and LLM explanation."""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding for Windows PowerShell / terminal compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root and backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

try:
    from backend.repo_processor import (
        clone_repo,
        get_relevant_files,
        read_files,
        build_file_tree,
    )
    from backend.llm_service import explain_repo
except ImportError:
    from repo_processor import (
        clone_repo,
        get_relevant_files,
        read_files,
        build_file_tree,
    )
    from llm_service import explain_repo


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/test_explain.py <github_repo_url>")
        print("Example: python backend/test_explain.py https://github.com/octocat/Hello-World")
        sys.exit(1)

    repo_url = sys.argv[1].strip()

    try:
        print(f"Cloning repository: {repo_url}...")
        repo_path = clone_repo(repo_url)
        print(f"Cloned successfully into: {repo_path}\n")

        print("Analyzing repository structure...")
        relevant_files = get_relevant_files(repo_path)
        file_tree = build_file_tree(repo_path, relevant_files)
        file_records = read_files(relevant_files, repo_path)
        print(f"Found {len(file_records)} relevant files.\n")

        print("Generating repository explanation using local Ollama model...")
        explanation = explain_repo(file_records, file_tree)

        print("\n" + "=" * 60)
        print("FINAL REPOSITORY EXPLANATION")
        print("=" * 60 + "\n")
        print(explanation)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
