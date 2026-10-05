"""Test script to test repository cloning and file processing functions."""

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
except ImportError:
    from repo_processor import (
        clone_repo,
        get_relevant_files,
        read_files,
        build_file_tree,
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/test_repo.py <github_repo_url>")
        print("Example: python backend/test_repo.py https://github.com/octocat/Hello-World")
        sys.exit(1)

    repo_url = sys.argv[1].strip()

    try:
        print(f"Cloning repository: {repo_url}...")
        repo_path = clone_repo(repo_url)
        print(f"Cloned successfully into: {repo_path}\n")

        print("Analyzing repository files...")
        relevant_files = get_relevant_files(repo_path)
        tree_text = build_file_tree(repo_path, relevant_files)
        file_records = read_files(relevant_files, repo_path)

        num_files = len(file_records)
        total_chars = sum(len(record["content"]) for record in file_records)

        print("\n--- File Tree ---")
        print(tree_text)
        print("\n--- Summary ---")
        print(f"Number of files: {num_files}")
        print(f"Total characters of code: {total_chars:,}")

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
